"""批改引擎 - 支持填空题、选择题、计算题"""
import re
import ast
import operator
from typing import Dict, List, Tuple

from fuzzywuzzy import fuzz

import config
from models.question import Question, QuestionType
from models.result import QuestionResult, GradingReport

# AST安全计算支持的运算符
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def grade_all(parsed_answers: Dict[int, str], questions: List[Question]) -> GradingReport:
    """批改所有题目，返回批改报告"""
    results = []
    for q in questions:
        recognized = parsed_answers.get(q.number, '')
        is_correct, match_score = _grade_single(q, recognized)
        earned = q.points * match_score if is_correct else 0.0
        results.append(QuestionResult(
            question=q,
            recognized_text=recognized,
            is_correct=is_correct,
            match_score=match_score,
            earned_points=round(earned, 2),
        ))
    return GradingReport(results=results)


def _grade_single(question: Question, recognized: str) -> Tuple[bool, float]:
    """根据题型分发批改"""
    if question.q_type == QuestionType.FILL_BLANK:
        return grade_fill_blank(recognized, question.standard_answer,
                                question.accept_alternatives)
    elif question.q_type == QuestionType.MULTIPLE_CHOICE:
        return grade_multiple_choice(recognized, question.standard_answer)
    elif question.q_type == QuestionType.CALCULATION:
        return grade_calculation(recognized, question.standard_answer)
    return False, 0.0


# ========== 填空题 ==========

def _normalize_text(text: str) -> str:
    """归一化文本：去空格、去标点"""
    text = text.strip()
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[，。、；：""''！？,.;:!?\'"·]', '', text)
    return text


def grade_fill_blank(recognized: str, standard: str,
                     alternatives: List[str] = None) -> Tuple[bool, float]:
    """填空题批改：精确匹配 + 模糊匹配"""
    rec = _normalize_text(recognized)
    std = _normalize_text(standard)

    if not rec:
        return False, 0.0

    # 精确匹配
    if rec == std:
        return True, 1.0

    # 检查备选答案
    if alternatives:
        for alt in alternatives:
            if rec == _normalize_text(alt):
                return True, 1.0

    # 模糊匹配
    ratio = fuzz.ratio(rec, std)
    if ratio >= config.FUZZY_MATCH_THRESHOLD:
        return True, ratio / 100.0

    # 部分匹配（处理OCR多识别了内容的情况）
    partial = fuzz.partial_ratio(rec, std)
    if partial >= config.PARTIAL_MATCH_THRESHOLD:
        return True, partial / 100.0 * 0.9

    return False, 0.0


# ========== 选择题 ==========

def _extract_choices(text: str) -> set:
    """从文本中提取选项字母"""
    text = text.upper()
    return set(re.findall(r'[A-F]', text))


def grade_multiple_choice(recognized: str, standard: str) -> Tuple[bool, float]:
    """选择题批改：字母精确匹配"""
    rec_choices = _extract_choices(recognized)
    std_choices = _extract_choices(standard)

    if not rec_choices:
        return False, 0.0

    if rec_choices == std_choices:
        return True, 1.0

    # 多选部分分（选对了部分且没选错）
    if rec_choices.issubset(std_choices) and len(std_choices) > 1:
        return False, len(rec_choices) / len(std_choices) * 0.5

    return False, 0.0


# ========== 计算题 ==========

def _normalize_math(text: str) -> str:
    """归一化数学符号"""
    replacements = {
        '×': '*', '✕': '*', 'Ｘ': '*', 'Ｘ': '*',
        '÷': '/', '➗': '/',
        '＝': '=', '＋': '+', '－': '-',
        '（': '(', '）': ')',
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.strip().replace(' ', '')


def _extract_numeric_answer(text: str) -> float:
    """从文本中提取数值答案"""
    text = _normalize_math(text)

    # 尝试提取等号后的数值
    if '=' in text:
        after_eq = text.split('=')[-1].strip()
        match = re.match(r'^[-]?\d+\.?\d*', after_eq)
        if match:
            return float(match.group())

    # 尝试作为纯数字解析
    match = re.match(r'^[-]?\d+\.?\d*$', text)
    if match:
        return float(text)

    # 尝试安全计算表达式
    try:
        return _safe_eval(text)
    except Exception:
        return None


def _safe_eval(expr: str) -> float:
    """使用AST安全计算数学表达式"""
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_func = _SAFE_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的运算符: {type(node.op)}")
        return op_func(left, right)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError(f"不支持的节点: {type(node)}")


def grade_calculation(recognized: str, standard: str) -> Tuple[bool, float]:
    """计算题批改：数值比较"""
    rec_val = _extract_numeric_answer(recognized)
    std_val = _extract_numeric_answer(standard)

    if rec_val is None or std_val is None:
        # 回退到字符串比较
        r = _normalize_math(recognized)
        s = _normalize_math(standard)
        return (r == s, 1.0) if r == s else (False, 0.0)

    if abs(std_val) < 1e-9:
        match = abs(rec_val) < 1e-9
    else:
        match = abs(rec_val - std_val) / max(abs(std_val), 1e-9) < config.CALCULATION_TOLERANCE

    return match, 1.0 if match else 0.0

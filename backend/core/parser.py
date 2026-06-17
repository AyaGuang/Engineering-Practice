"""
* QuestionResultRecord class
* OCR结果解析模块 - 将OCR文本解析为题号-答案对
* create by 廖帅
* copyright USTC
* 2026.02.23
"""
import re
from typing import Dict, List, Tuple

from models.question import OcrResult

# 题号匹配模式
QUESTION_NUMBER_PATTERNS = [
    re.compile(r'^[（(]\s*(\d+)\s*[）)]\s*[.、:：]?\s*(.*)'),   # (1) 或 （1）
    re.compile(r'^第\s*(\d+)\s*题\s*[.、:：]?\s*(.*)'),         # 第1题
    re.compile(r'^例\s*(\d+)\s*[.、:：．]?\s*(.*)'),            # 例1 或 例1.
    re.compile(r'^(\d+)\s*[.、)\）:：]\s*(.*)'),                # 1. 或 1、或 1)
    re.compile(r'^(\d+)\s*[．]\s*(.*)'),                        # 1．(全角句点)
]

# 选项前缀：字母(A-D) + 分隔符(. 、 ) ）)
_OPTION_PREFIX = re.compile(r'[A-Da-d]\s*[.、)）]')


def _is_options_line(text: str) -> bool:
    """
    检测一行是否为选择题选项行。
    形态1：以"A." "B、" "C)" 这类开头（单选项独占一行）
    形态2：一行内出现2个以上选项前缀（多选项挤在一行，如"A.9B.6C.5D.4"）
    """
    text = text.strip()
    if not text:
        return False
    if re.match(r'^[A-Da-d]\s*[.、)）]', text):
        return True
    if len(_OPTION_PREFIX.findall(text)) >= 2:
        return True
    return False


def parse_answers(ocr_results: List[OcrResult],
                  skip_options: bool = False) -> Dict[int, str]:
    """
    将OCR识别结果解析为 {题号: 答案文本} 字典。
    支持多行答案合并；题号撞号时先到先得（保留首次，孤立后续重复区域）。

    Args:
        skip_options: 开启选择题增强时，跳过选项行（A.B.C.D.）避免污染答案
    """
    if not ocr_results:
        return {}

    parsed = {}
    current_qnum = None

    for result in ocr_results:
        text = result.text.strip()
        if not text:
            continue

        qnum, answer_text = _try_extract_question(text)

        if qnum is not None:
            if qnum not in parsed:
                # 首次出现该题号：建立记录
                current_qnum = qnum
                parsed[current_qnum] = answer_text
            else:
                # 题号撞号：先到先得，保留首次内容。
                # 孤立后续重复区域，避免嵌套内容污染其他题目。
                current_qnum = None
        elif current_qnum is not None:
            # 选择题增强：选项行不污染答案（答案已在题干括号里）
            if skip_options and _is_options_line(text):
                continue
            # 续行，追加到当前题目
            parsed[current_qnum] += text

    return parsed


def parse_answers_by_position(ocr_results: List[OcrResult],
                              skip_options: bool = False) -> List[Tuple[int, str]]:
    """
    按位置顺序解析OCR结果，保留所有题号（含重复/嵌套）。
    用于位置匹配模式：识别出的每道题按出现顺序组成列表，
    与标准答案列表按下标一一对应（多退少补）。

    Args:
        skip_options: 开启选择题增强时，跳过选项行避免污染答案

    Returns:
        [(题号, 答案文本), ...] —— 按OCR出现顺序，题号可能重复
    """
    if not ocr_results:
        return []

    parsed = []
    current_idx = None  # 当前题在 parsed 中的下标

    for result in ocr_results:
        text = result.text.strip()
        if not text:
            continue

        qnum, answer_text = _try_extract_question(text)

        if qnum is not None:
            # 遇到题号（含重复）：追加为新条目
            current_idx = len(parsed)
            parsed.append((qnum, answer_text))
        elif current_idx is not None:
            # 选择题增强：选项行不污染答案
            if skip_options and _is_options_line(text):
                continue
            # 续行，追加到当前题
            qnum, ans = parsed[current_idx]
            parsed[current_idx] = (qnum, ans + text)

    return parsed


def _try_extract_question(text: str):
    """尝试从文本中提取题号和答案。返回 (题号, 答案文本) 或 (None, None)"""
    for pattern in QUESTION_NUMBER_PATTERNS:
        match = pattern.match(text)
        if match:
            qnum = int(match.group(1))
            answer = match.group(2).strip() if match.lastindex >= 2 else ''
            return qnum, answer
    return None, None

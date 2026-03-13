"""
* QuestionResultRecord class
* OCR结果解析模块 - 将OCR文本解析为题号-答案对
* create by 廖帅
* copyright USTC
* 2026.02.23
"""
import re
from typing import Dict, List

from models.question import OcrResult

# 题号匹配模式
QUESTION_NUMBER_PATTERNS = [
    re.compile(r'^[（(]\s*(\d+)\s*[）)]\s*[.、:：]?\s*(.*)'),   # (1) 或 （1）
    re.compile(r'^第\s*(\d+)\s*题\s*[.、:：]?\s*(.*)'),         # 第1题
    re.compile(r'^例\s*(\d+)\s*[.、:：．]?\s*(.*)'),            # 例1 或 例1.
    re.compile(r'^(\d+)\s*[.、)\）:：]\s*(.*)'),                # 1. 或 1、或 1)
    re.compile(r'^(\d+)\s*[．]\s*(.*)'),                        # 1．(全角句点)
]


def parse_answers(ocr_results: List[OcrResult]) -> Dict[int, str]:
    """
    将OCR识别结果解析为 {题号: 答案文本} 字典。
    支持多行答案合并。
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
            current_qnum = qnum
            parsed[current_qnum] = answer_text
        elif current_qnum is not None:
            # 续行，追加到当前题目
            parsed[current_qnum] += text

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

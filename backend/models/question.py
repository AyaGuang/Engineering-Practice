from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


"""
* QuestionType class
* 题目类型枚举类，定义填空题、选择题、计算题三种题型及其显示名称
* create by 林睿埼
* copyright USTC
* 2026.02.05
"""
class QuestionType(Enum):
    FILL_BLANK = "fill_blank"
    MULTIPLE_CHOICE = "multiple_choice"
    CALCULATION = "calculation"

    @property
    def display_name(self):
        names = {
            "fill_blank": "填空题",
            "multiple_choice": "选择题",
            "calculation": "计算题",
        }
        return names[self.value]


"""
* Question class
* 题目数据类，包含题号、题型、标准答案、分值及可接受的替代答案
* create by 林睿埼
* copyright USTC
* 2026.02.05
"""
@dataclass
class Question:
    number: int
    q_type: QuestionType
    standard_answer: str
    points: float = 1.0
    accept_alternatives: List[str] = field(default_factory=list)


"""
* OcrResult class
* OCR识别结果数据类，存储文本区域的边界框坐标、识别文本及置信度
* create by 林睿埼
* copyright USTC
* 2026.02.05
"""
@dataclass
class OcrResult:
    bbox: List[List[int]]
    text: str
    confidence: float

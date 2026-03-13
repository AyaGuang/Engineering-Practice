from dataclasses import dataclass
from typing import List
from .question import Question


"""
* QuestionResult class
* 单题批改结果数据类，记录识别文本、是否正确、匹配度和得分
* create by XXX
* copyright USTC
* 时间
"""
@dataclass
class QuestionResult:
    question: Question
    recognized_text: str
    is_correct: bool
    match_score: float       # 0.0 ~ 1.0
    earned_points: float


"""
* GradingReport class
* 批改报告数据类，汇总所有题目的批改结果，计算总分和得分率
* create by XXX
* copyright USTC
* 时间
"""
@dataclass
class GradingReport:
    results: List[QuestionResult]

    @property
    def total_points(self) -> float:
        return sum(r.question.points for r in self.results)

    @property
    def earned_points(self) -> float:
        return sum(r.earned_points for r in self.results)

    @property
    def percentage(self) -> float:
        if self.total_points == 0:
            return 0.0
        return self.earned_points / self.total_points * 100

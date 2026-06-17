"""
* LLMCorrector class
* LLM OCR纠错引擎 - 调用OpenAI API纠正手写作业OCR识别错误
* create by 林文光
* copyright USTC
* 2026.06.12
"""
import json
import logging
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from models.question import OcrResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是一位中文手写作业OCR纠错与答案匹配助手。

任务：根据待批改题目列表，纠正OCR识别错误，并把每道题对应的识别内容匹配出来。

规则：
1. 修正OCR的明显错误（形近字、中文"等于/相加"、中文数字"一二三"、选择题字母等）。
2. 理解题目层级结构（①②③序号、嵌套题号如第7题下的(1)(2)），把每道题对应的识别内容提取出来。
3. 按题型提取真正的答案：
   - 填空题(calculation/fill_blank)：提取核心答案，精简冗长表述。例如"1和2相加等于3"→"3"。
   - 选择题(multiple_choice)：只提取选项字母（A/B/C/D），不要改动字母本身。
   - 如果选择题识别到多个方括号内单选项内容，说明属于答题卡选择题(如[A][C][D]，意为题者将[A][B][C][D]中的B涂黑识别不到了,此时应输出B)
4. matched_answers的key必须严格使用待批改题目列表里的题号（number字段的字符串形式）。
5. 某题在OCR中找不到对应内容时，对应值留空字符串""。
6. 不要把题目说明性文字（如"共7小题25分"）当作答案。

输出严格JSON，不要其他文字：
{
  "corrections": [{"index": 0, "corrected_text": "纠正后的文本", "changed": true}, ...],
  "matched_answers": {"1": "安定", "2": "A", "3": ""}
}"""


class LLMCorrector:
    """调用OpenAI API纠正OCR识别结果"""

    def __init__(self, api_key: str, model: str = 'gpt-4o-mini',
                 base_url: Optional[str] = None, timeout: int = 30):
        kwargs = {'api_key': api_key, 'timeout': timeout}
        if base_url:
            kwargs['base_url'] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def correct(self, ocr_results: List[OcrResult],
                questions: List[dict] = None) -> Tuple[List[OcrResult], int, Dict[str, str]]:
        """
        纠正OCR文本并匹配答案，保持bbox/confidence不变。

        Args:
            ocr_results: 原始OCR识别结果
            questions: 待批改题目列表，每项含 number/type/answer 等字段。
                       提供时LLM会输出 matched_answers（题号→识别答案）。

        Returns:
            (纠正后的OcrResult列表, 修正数量, 匹配答案字典)
            匹配失败或未提供questions时，matched_answers为空字典。
        """
        if not ocr_results:
            return ocr_results, 0, {}

        user_content = self._build_user_content(ocr_results, questions)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_content},
                ],
                temperature=0.1,
                response_format={'type': 'json_object'},
            )
            return self._parse_response(ocr_results, response)
        except Exception as e:
            logger.warning('LLM纠错调用失败: %s', e)
            return ocr_results, 0, {}

    def _build_user_content(self, ocr_results: List[OcrResult],
                            questions: List[dict] = None) -> str:
        lines = ['OCR识别结果（共%d条）：' % len(ocr_results)]
        for i, r in enumerate(ocr_results):
            lines.append('[%d] text="%s" confidence=%.2f'
                         % (i, r.text, r.confidence))

        if questions:
            lines.append('')
            lines.append('待批改题目列表（共%d题）：' % len(questions))
            for q in questions:
                lines.append('题号:%s 类型:%s 标准答案:%s'
                             % (q.get('number', ''), q.get('type', ''),
                                q.get('answer', '')))
            lines.append('')
            lines.append('请纠正OCR错误，并输出 matched_answers（key用题号字符串，'
                          'value为该题对应的识别答案）。')

        return '\n'.join(lines)

    def _parse_response(self, ocr_results: List[OcrResult],
                        response) -> Tuple[List[OcrResult], int, Dict[str, str]]:
        content = response.choices[0].message.content
        if not content:
            return ocr_results, 0, {}

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning('LLM返回非法JSON: %s', content[:200])
            return ocr_results, 0, {}

        # 解析纠错结果
        corrections = data.get('corrections', [])
        if not isinstance(corrections, list):
            corrections = []

        corrected = list(ocr_results)
        change_count = 0
        for item in corrections:
            idx = item.get('index')
            text = item.get('corrected_text')
            changed = item.get('changed', False)
            if (isinstance(idx, int) and 0 <= idx < len(corrected)
                    and text and changed):
                corrected[idx] = OcrResult(
                    bbox=corrected[idx].bbox,
                    text=text,
                    confidence=corrected[idx].confidence,
                )
                change_count += 1

        # 解析匹配答案
        matched = data.get('matched_answers', {})
        if not isinstance(matched, dict):
            matched = {}

        return corrected, change_count, matched

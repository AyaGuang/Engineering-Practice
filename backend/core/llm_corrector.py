"""
* LLMCorrector class
* LLM OCR纠错引擎 - 调用OpenAI API纠正手写作业OCR识别错误
* create by 希芙
* copyright USTC
* 2026.06.12
"""
import json
import logging
from typing import List, Optional, Tuple

from openai import OpenAI

from models.question import OcrResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是一位专业的中文手写作业OCR纠错助手。

任务：纠正以下OCR识别结果中的明显错误。

规则：
1. 只修正明显的识别错误（形近字、偏旁部首错误等）
2. 不确定的文本保持原样，不要猜测
3. 保留原始的题号格式、标点符号和换行结构
4. 数学表达式中的数字和运算符要特别仔细检查
5. 返回JSON数组格式

输出格式（严格JSON数组，不要其他文字）：
[{"index": 0, "corrected_text": "纠正后的文本", "changed": true/false}, ...]"""


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
                context: str = '') -> Tuple[List[OcrResult], int]:
        """
        纠正OCR文本，保持bbox/confidence不变。

        Args:
            ocr_results: 原始OCR识别结果
            context: 标准答案摘要，帮助LLM判断纠错方向

        Returns:
            (纠正后的OcrResult列表, 修正数量)
        """
        if not ocr_results:
            return ocr_results, 0

        user_content = self._build_user_content(ocr_results, context)

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
            return ocr_results, 0

    def _build_user_content(self, ocr_results: List[OcrResult],
                            context: str) -> str:
        lines = ['OCR识别结果（共%d条）：' % len(ocr_results)]
        for i, r in enumerate(ocr_results):
            lines.append('[%d] text="%s" confidence=%.2f'
                         % (i, r.text, r.confidence))
        if context:
            lines.append('')
            lines.append('参考信息（标准答案摘要）：')
            lines.append(context)
        lines.append('')
        lines.append('请纠正以上OCR结果中的明显错误，返回JSON。'
                      'JSON的key为"corrections"，值为数组。')
        return '\n'.join(lines)

    def _parse_response(self, ocr_results: List[OcrResult],
                        response) -> Tuple[List[OcrResult], int]:
        content = response.choices[0].message.content
        if not content:
            return ocr_results, 0

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning('LLM返回非法JSON: %s', content[:200])
            return ocr_results, 0

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

        return corrected, change_count

"""文本解析模块单元测试"""
import unittest
from models.question import OcrResult
from core.parser import parse_answers


"""
* TestParser class
* 文本解析模块的单元测试类，验证多种题号格式解析和多行答案合并等场景
* create by XXX
* copyright USTC
* 时间
"""
class TestParser(unittest.TestCase):
    def _make_result(self, text, y=0, x=0):
        return OcrResult(bbox=[[x, y], [x+100, y], [x+100, y+30], [x, y+30]],
                         text=text, confidence=0.9)

    def test_dot_format(self):
        results = [
            self._make_result("1.北京", y=0),
            self._make_result("2.上海", y=50),
        ]
        parsed = parse_answers(results)
        self.assertEqual(parsed[1], "北京")
        self.assertEqual(parsed[2], "上海")

    def test_chinese_format(self):
        results = [
            self._make_result("1、B", y=0),
            self._make_result("2、C", y=50),
        ]
        parsed = parse_answers(results)
        self.assertEqual(parsed[1], "B")
        self.assertEqual(parsed[2], "C")

    def test_parenthesis_format(self):
        results = [
            self._make_result("(1) 答案一", y=0),
            self._make_result("(2) 答案二", y=50),
        ]
        parsed = parse_answers(results)
        self.assertEqual(parsed[1], "答案一")
        self.assertEqual(parsed[2], "答案二")

    def test_multiline_answer(self):
        results = [
            self._make_result("1.北京是", y=0),
            self._make_result("中国的首都", y=30),
            self._make_result("2.B", y=80),
        ]
        parsed = parse_answers(results)
        self.assertEqual(parsed[1], "北京是中国的首都")
        self.assertEqual(parsed[2], "B")

    def test_empty_results(self):
        parsed = parse_answers([])
        self.assertEqual(parsed, {})

    def test_di_format(self):
        results = [
            self._make_result("第1题 42", y=0),
        ]
        parsed = parse_answers(results)
        self.assertEqual(parsed[1], "42")


if __name__ == '__main__':
    unittest.main()

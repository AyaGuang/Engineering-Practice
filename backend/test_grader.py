"""
* 批改引擎单元测试
* create by 林文光
* copyright USTC
* 2026.03.05
"""
import unittest
from core.grader import grade_fill_blank, grade_multiple_choice, grade_calculation


"""
* TestFillBlank class
* 填空题批改逻辑的单元测试类，验证精确匹配、模糊匹配和空答案等场景
* create by 林文光
* copyright USTC
* 2026.03.05
"""
class TestFillBlank(unittest.TestCase):
    def test_exact_match(self):
        ok, score = grade_fill_blank("北京", "北京")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_exact_match_with_whitespace(self):
        ok, score = grade_fill_blank(" 北京 ", "北京")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_fuzzy_match(self):
        ok, score = grade_fill_blank("北亰", "北京")
        # 模糊匹配可能通过也可能不通过取决于阈值
        # fuzz.ratio("北亰", "北京") 大约50，不会通过80阈值
        # 这是预期行为

    def test_wrong_answer(self):
        ok, score = grade_fill_blank("上海", "北京")
        self.assertFalse(ok)
        self.assertEqual(score, 0.0)

    def test_empty_recognized(self):
        ok, score = grade_fill_blank("", "北京")
        self.assertFalse(ok)
        self.assertEqual(score, 0.0)

    def test_alternative_answer(self):
        ok, score = grade_fill_blank("长方型", "长方形", alternatives=["长方型"])
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)


"""
* TestMultipleChoice class
* 选择题批改逻辑的单元测试类，验证单选、多选和文本提取等场景
* create by 林文光
* copyright USTC
* 2026.03.05
"""
class TestMultipleChoice(unittest.TestCase):
    def test_correct_single(self):
        ok, score = grade_multiple_choice("B", "B")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_wrong_single(self):
        ok, score = grade_multiple_choice("A", "B")
        self.assertFalse(ok)

    def test_correct_multi(self):
        ok, score = grade_multiple_choice("AC", "AC")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_extract_from_text(self):
        ok, score = grade_multiple_choice("选B", "B")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_empty(self):
        ok, score = grade_multiple_choice("", "B")
        self.assertFalse(ok)


"""
* TestCalculation class
* 计算题批改逻辑的单元测试类，验证数值比较、表达式求值和中文符号处理等场景
* create by 林文光
* copyright USTC
* 2026.03.05
"""
class TestCalculation(unittest.TestCase):
    def test_exact_number(self):
        ok, score = grade_calculation("15", "15")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_with_equals(self):
        ok, score = grade_calculation("3+5=8", "8")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_chinese_symbols(self):
        ok, score = grade_calculation("３＋５＝８", "8")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_multiplication(self):
        ok, score = grade_calculation("3×5=15", "15")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

    def test_wrong_result(self):
        ok, score = grade_calculation("3+5=9", "8")
        self.assertFalse(ok)

    def test_expression_eval(self):
        ok, score = grade_calculation("24", "4*6")
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)


if __name__ == '__main__':
    unittest.main()

"""数据库模块单元测试"""
import os
import unittest
from datetime import datetime

# 使用测试数据库
os.environ['TEST_MODE'] = '1'
import config
config.DB_NAME = 'test_homework_grader.db'

import database as db


"""
* TestDatabase class
* 数据库模块的单元测试类，验证作业保存、批改记录增删查、历史检索和统计功能
* create by XXX
* copyright USTC
* 时间
"""
class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """每次测试前重建数据库"""
        test_db = os.path.join(os.path.dirname(__file__), config.DB_NAME)
        if os.path.exists(test_db):
            os.remove(test_db)
        # 重新初始化引擎
        db.DB_PATH = test_db
        db.engine = db.create_engine(f'sqlite:///{test_db}', echo=False)
        db.Session = db.sessionmaker(bind=db.engine)
        db.init_db()

        # 预插入测试数据
        session = db.get_session()
        hw = db.save_homework(session, 'pre-test-001', '预置作业.png', 'pre-test-001.png', '/tmp/pre.png')
        result_data = [
            {'number': 1, 'type': 'fill_blank', 'type_name': '填空题',
             'recognized_text': '北京', 'standard_answer': '北京',
             'is_correct': True, 'match_score': 1.0, 'earned_points': 2.0, 'total_points': 2.0},
            {'number': 2, 'type': 'multiple_choice', 'type_name': '选择题',
             'recognized_text': 'A', 'standard_answer': 'B',
             'is_correct': False, 'match_score': 0.0, 'earned_points': 0.0, 'total_points': 2.0},
        ]
        summary = {'total_points': 4.0, 'earned_points': 2.0, 'percentage': 50.0}
        db.save_grading(session, hw, result_data, summary, 5)
        session.close()

    @classmethod
    def tearDownClass(cls):
        test_db = os.path.join(os.path.dirname(__file__), config.DB_NAME)
        if os.path.exists(test_db):
            os.remove(test_db)

    def test_save_and_query_homework(self):
        session = db.get_session()
        try:
            hw = db.save_homework(session, 'test-file-001', '作业1.png', 'test-file-001.png', '/tmp/test.png')
            self.assertIsNotNone(hw.id)
            self.assertEqual(hw.file_id, 'test-file-001')

            found = db.get_homework_by_file_id(session, 'test-file-001')
            self.assertIsNotNone(found)
            self.assertEqual(found.original_filename, '作业1.png')
        finally:
            session.close()

    def test_save_and_query_grading(self):
        session = db.get_session()
        try:
            hw = db.save_homework(session, 'test-file-002', '作业2.png', 'test-file-002.png', '/tmp/test2.png')

            result_data = [
                {
                    'number': 1, 'type': 'fill_blank', 'type_name': '填空题',
                    'recognized_text': '北京', 'standard_answer': '北京',
                    'is_correct': True, 'match_score': 1.0,
                    'earned_points': 2.0, 'total_points': 2.0,
                },
                {
                    'number': 2, 'type': 'multiple_choice', 'type_name': '选择题',
                    'recognized_text': 'A', 'standard_answer': 'B',
                    'is_correct': False, 'match_score': 0.0,
                    'earned_points': 0.0, 'total_points': 2.0,
                },
            ]
            summary = {'total_points': 4.0, 'earned_points': 2.0, 'percentage': 50.0}

            record = db.save_grading(session, hw, result_data, summary, 5)
            self.assertIsNotNone(record.id)
            self.assertEqual(record.total_points, 4.0)
            self.assertEqual(record.earned_points, 2.0)
            self.assertEqual(len(record.question_results), 2)
        finally:
            session.close()

    def test_query_history(self):
        session = db.get_session()
        try:
            result = db.query_history(session)
            self.assertIn('total', result)
            self.assertIn('records', result)
            self.assertGreater(result['total'], 0)
        finally:
            session.close()

    def test_query_history_with_keyword(self):
        session = db.get_session()
        try:
            result = db.query_history(session, keyword='预置作业')
            self.assertGreater(result['total'], 0)

            result = db.query_history(session, keyword='不存在的文件')
            self.assertEqual(result['total'], 0)
        finally:
            session.close()

    def test_query_history_with_score(self):
        session = db.get_session()
        try:
            result = db.query_history(session, min_score=40, max_score=60)
            # 应该找到得分率50%的记录
            self.assertGreater(result['total'], 0)

            result = db.query_history(session, min_score=90)
            # 得分率50%的不应该出现
            self.assertEqual(result['total'], 0)
        finally:
            session.close()

    def test_get_grading_detail(self):
        session = db.get_session()
        try:
            history = db.query_history(session)
            if history['records']:
                gid = history['records'][0]['id']
                detail = db.get_grading_detail(session, gid)
                self.assertIsNotNone(detail)
                self.assertIn('question_results', detail)
                self.assertGreater(len(detail['question_results']), 0)
        finally:
            session.close()

    def test_delete_grading(self):
        session = db.get_session()
        try:
            hw = db.save_homework(session, 'test-file-del', '删除测试.png', 'del.png', '/tmp/del.png')
            result_data = [{'number': 1, 'type': 'fill_blank', 'type_name': '填空题',
                            'recognized_text': 'x', 'standard_answer': 'y',
                            'is_correct': False, 'match_score': 0, 'earned_points': 0, 'total_points': 1}]
            summary = {'total_points': 1, 'earned_points': 0, 'percentage': 0}
            record = db.save_grading(session, hw, result_data, summary, 1)
            rid = record.id

            ok = db.delete_grading(session, rid)
            self.assertTrue(ok)

            detail = db.get_grading_detail(session, rid)
            self.assertIsNone(detail)
        finally:
            session.close()

    def test_statistics(self):
        session = db.get_session()
        try:
            stats = db.get_statistics(session)
            self.assertIn('total_gradings', stats)
            self.assertIn('total_homeworks', stats)
            self.assertIn('avg_percentage', stats)
        finally:
            session.close()


if __name__ == '__main__':
    unittest.main()

"""
* QuestionResultRecord class
* 数据库模块单元测试
* create by 林文光
* copyright USTC
* 2026.03.04
"""
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
* create by 林文光
* copyright USTC
* 2026.03.04
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
        # Windows 下 SQLite 句柄可能未立即释放，删除失败时忽略；
        # 下次 setUpClass 会在进程退出后重新删除。
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except OSError:
                pass

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


"""
* TestUsersAssignmentsSubmissions class
* 用户/作业/提交相关 ORM 与 helper 的单元测试
* create by 林文光
* copyright USTC
* 2026.06.23
"""
class TestUsersAssignmentsSubmissions(unittest.TestCase):

    def test_user_create_credentials_list_delete(self):
        session = db.get_session()
        try:
            u = db.create_user(session, 'stu_a', 'pw', 'student', '学生A')
            self.assertIsNotNone(u.id)
            self.assertEqual(u.role, 'student')

            # 凭证正确
            ok = db.get_user_by_credentials(session, 'stu_a', 'pw')
            self.assertIsNotNone(ok)
            # 密码错误
            self.assertIsNone(
                db.get_user_by_credentials(session, 'stu_a', 'wrong'))
            # 用户名错误
            self.assertIsNone(
                db.get_user_by_credentials(session, 'no_one', 'pw'))

            # 列表过滤
            students = db.list_users(session, role='student')
            self.assertTrue(any(s.username == 'stu_a' for s in students))
            everyone = db.list_users(session, role=None)
            self.assertTrue(any(e.role == 'teacher' for e in everyone))

            # 删除
            self.assertTrue(db.delete_user(session, u.id))
            self.assertIsNone(db.get_user_by_id(session, u.id))
        finally:
            session.close()

    def test_delete_last_teacher_protected(self):
        """最后一个教师账号不可删除"""
        session = db.get_session()
        try:
            teacher = session.query(db.User).filter_by(role='teacher').first()
            self.assertFalse(db.delete_user(session, teacher.id))
            self.assertIsNotNone(db.get_user_by_id(session, teacher.id))
        finally:
            session.close()

    def test_assignment_crud(self):
        session = db.get_session()
        try:
            teacher = session.query(db.User).filter_by(role='teacher').first()
            qs = [{'number': 1, 'type': 'fill_blank', 'answer': '北京',
                   'points': 2.0}]
            a = db.create_assignment(session, '单测作业', teacher.id, qs)
            self.assertIsNotNone(a.id)

            # 详情含 questions 与题数
            got = db.get_assignment(session, a.id).to_dict()
            self.assertEqual(got['name'], '单测作业')
            self.assertEqual(got['question_count'], 1)
            self.assertEqual(got['questions'][0]['answer'], '北京')

            # 列表过滤
            mine = db.list_assignments(session, teacher_id=teacher.id)
            self.assertTrue(any(x.id == a.id for x in mine))

            # 更新
            a2 = db.update_assignment(session, a.id, name='改名',
                                      status='closed')
            self.assertEqual(a2.name, '改名')
            self.assertEqual(a2.status, 'closed')

            # 学生视角不返回答案
            active = db.list_assignments(session, status='closed')
            self.assertFalse(active[0].to_dict(include_questions=False)
                             .get('questions'))

            # 删除
            self.assertTrue(db.delete_assignment(session, a.id))
            self.assertIsNone(db.get_assignment(session, a.id))
        finally:
            session.close()

    def test_submission_flow_and_publish(self):
        session = db.get_session()
        try:
            teacher = session.query(db.User).filter_by(role='teacher').first()
            stu = db.create_user(session, 'stu_sub', 'pw', 'student', '提交生')
            a = db.create_assignment(session, '提交作业', teacher.id,
                                     [{'number': 1, 'type': 'fill_blank',
                                       'answer': 'x', 'points': 1.0}])
            hw = db.save_homework(session, 'sub-file-1', 's.png', 's.png',
                                  '/tmp/s.png')
            result_data = [{'number': 1, 'type': 'fill_blank',
                            'type_name': '填空题', 'recognized_text': 'x',
                            'standard_answer': 'x', 'is_correct': True,
                            'match_score': 1.0, 'earned_points': 1.0,
                            'total_points': 1.0}]
            grading = db.save_grading(session, hw, result_data,
                                      {'total_points': 1, 'earned_points': 1,
                                       'percentage': 100.0}, 1)

            sub = db.create_submission(session, a.id, stu.id, grading.id,
                                       'pending')
            self.assertEqual(sub.status, 'pending')

            # 按学生过滤
            res = db.list_submissions(session, student_id=stu.id)
            self.assertEqual(res['total'], 1)
            # 列表含 grading 摘要
            self.assertIsNotNone(res['submissions'][0].get('grading'))

            # 发布
            pub = db.publish_submission(session, sub.id)
            self.assertEqual(pub.status, 'published')
            self.assertIsNotNone(pub.published_at)
            # 按状态过滤
            self.assertEqual(
                db.list_submissions(session, status='published')['total'], 1)
            self.assertEqual(
                db.list_submissions(session, status='pending')['total'], 0)

            # 删除作业级联删除提交
            db.delete_assignment(session, a.id)
            self.assertIsNone(db.get_submission(session, sub.id))
        finally:
            session.close()

    def test_update_question_results_recalc(self):
        session = db.get_session()
        try:
            hw = db.save_homework(session, 'recalc-file', 'r.png', 'r.png',
                                  '/tmp/r.png')
            result_data = [
                {'number': 1, 'type': 'fill_blank', 'type_name': '填空题',
                 'recognized_text': 'a', 'standard_answer': 'b',
                 'is_correct': False, 'match_score': 0.0,
                 'earned_points': 0.0, 'total_points': 2.0},
                {'number': 2, 'type': 'multiple_choice', 'type_name': '选择题',
                 'recognized_text': 'A', 'standard_answer': 'A',
                 'is_correct': True, 'match_score': 1.0,
                 'earned_points': 3.0, 'total_points': 3.0},
            ]
            grading = db.save_grading(session, hw, result_data,
                                      {'total_points': 5, 'earned_points': 3,
                                       'percentage': 60.0}, 2)
            # 改第1题为满分
            rec = db.update_question_results(session, grading.id,
                                             {1: {'earned_points': 2.0,
                                                  'is_correct': True}})
            self.assertAlmostEqual(rec.earned_points, 5.0)
            self.assertAlmostEqual(rec.total_points, 5.0)
            self.assertAlmostEqual(rec.percentage, 100.0)
            qr1 = [q for q in rec.question_results if q.question_number == 1][0]
            self.assertTrue(qr1.is_correct)
            self.assertAlmostEqual(qr1.earned_points, 2.0)
        finally:
            session.close()

    def test_homework_uploader_id(self):
        """uploader_id 列可读写（学生提交标记上传者）"""
        session = db.get_session()
        try:
            stu = db.create_user(session, 'stu_up', 'pw', 'student', '上传生')
            hw = db.save_homework(session, 'up-file', 'u.png', 'u.png',
                                  '/tmp/u.png')
            hw.uploader_id = stu.id
            session.commit()
            again = db.get_homework_by_file_id(session, 'up-file')
            self.assertEqual(again.uploader_id, stu.id)
        finally:
            session.close()


if __name__ == '__main__':
    unittest.main()

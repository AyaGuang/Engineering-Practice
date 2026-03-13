"""数据库模块 - SQLite + SQLAlchemy ORM"""
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import config

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), config.DB_NAME)
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


# ============ ORM模型 ============

"""
* Homework class
* 作业上传记录ORM模型，映射homeworks表，存储上传的作业图片信息
* create by 廖帅
* copyright USTC
* 2026.02.06
"""
class Homework(Base):
    __tablename__ = 'homeworks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(64), unique=True, nullable=False, index=True)
    original_filename = Column(String(256))
    stored_filename = Column(String(256))
    upload_time = Column(DateTime, default=datetime.now)
    image_path = Column(String(512))

    # 关联批改记录
    gradings = relationship('GradingRecord', back_populates='homework',
                            cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'original_filename': self.original_filename,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
        }


"""
* GradingRecord class
* 批改记录ORM模型，映射grading_records表，存储每次批改的总分、得分和得分率
* create by 廖帅
* copyright USTC
* 2026.02.06
"""
class GradingRecord(Base):
    __tablename__ = 'grading_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    homework_id = Column(Integer, ForeignKey('homeworks.id'), nullable=False)
    grade_time = Column(DateTime, default=datetime.now)
    total_points = Column(Float, default=0)
    earned_points = Column(Float, default=0)
    percentage = Column(Float, default=0)
    ocr_count = Column(Integer, default=0)

    # 关联
    homework = relationship('Homework', back_populates='gradings')
    question_results = relationship('QuestionResultRecord', back_populates='grading',
                                    cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'homework_id': self.homework_id,
            'file_id': self.homework.file_id if self.homework else None,
            'original_filename': self.homework.original_filename if self.homework else None,
            'grade_time': self.grade_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_points': self.total_points,
            'earned_points': self.earned_points,
            'percentage': round(self.percentage, 2),
            'ocr_count': self.ocr_count,
            'question_results': [qr.to_dict() for qr in self.question_results],
        }


"""
* QuestionResultRecord class
* 每题批改结果ORM模型，映射question_results表，记录每道题的识别文本、标准答案和得分
* create by 廖帅
* copyright USTC
* 2026.02.06
"""
class QuestionResultRecord(Base):
    __tablename__ = 'question_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    grading_id = Column(Integer, ForeignKey('grading_records.id'), nullable=False)
    question_number = Column(Integer)
    question_type = Column(String(32))
    question_type_name = Column(String(32))
    recognized_text = Column(Text, default='')
    standard_answer = Column(Text, default='')
    is_correct = Column(Boolean, default=False)
    match_score = Column(Float, default=0)
    earned_points = Column(Float, default=0)
    total_points = Column(Float, default=0)

    grading = relationship('GradingRecord', back_populates='question_results')

    def to_dict(self):
        return {
            'number': self.question_number,
            'type': self.question_type,
            'type_name': self.question_type_name,
            'recognized_text': self.recognized_text,
            'standard_answer': self.standard_answer,
            'is_correct': self.is_correct,
            'match_score': self.match_score,
            'earned_points': self.earned_points,
            'total_points': self.total_points,
        }


# ============ 数据库操作 ============

def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(engine)


def get_session():
    """获取数据库会话"""
    return Session()


def save_homework(session, file_id, original_filename, stored_filename, image_path):
    """保存作业上传记录"""
    hw = Homework(
        file_id=file_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        image_path=image_path,
    )
    session.add(hw)
    session.commit()
    return hw


def save_grading(session, homework, result_data, summary, ocr_count):
    """保存批改结果"""
    record = GradingRecord(
        homework_id=homework.id,
        total_points=summary.get('total_points', 0),
        earned_points=summary.get('earned_points', 0),
        percentage=summary.get('percentage', 0),
        ocr_count=ocr_count,
    )
    session.add(record)
    session.flush()  # 获取record.id

    for r in result_data:
        qr = QuestionResultRecord(
            grading_id=record.id,
            question_number=r.get('number', 0),
            question_type=r.get('type', ''),
            question_type_name=r.get('type_name', ''),
            recognized_text=r.get('recognized_text', ''),
            standard_answer=r.get('standard_answer', ''),
            is_correct=r.get('is_correct', False),
            match_score=r.get('match_score', 0),
            earned_points=r.get('earned_points', 0),
            total_points=r.get('total_points', 0),
        )
        session.add(qr)

    session.commit()
    return record


def get_homework_by_file_id(session, file_id):
    """根据file_id查询作业"""
    return session.query(Homework).filter_by(file_id=file_id).first()


def query_history(session, keyword=None, date_from=None, date_to=None,
                  min_score=None, max_score=None, page=1, per_page=20):
    """
    查询批改历史记录，支持多条件检索。
    keyword: 按原始文件名模糊搜索
    date_from/date_to: 按批改时间范围过滤
    min_score/max_score: 按得分率过滤
    """
    q = session.query(GradingRecord).join(Homework)

    if keyword:
        q = q.filter(Homework.original_filename.like(f'%{keyword}%'))

    if date_from:
        q = q.filter(GradingRecord.grade_time >= date_from)

    if date_to:
        q = q.filter(GradingRecord.grade_time <= date_to)

    if min_score is not None:
        q = q.filter(GradingRecord.percentage >= min_score)

    if max_score is not None:
        q = q.filter(GradingRecord.percentage <= max_score)

    total = q.count()
    records = q.order_by(GradingRecord.grade_time.desc()) \
               .offset((page - 1) * per_page) \
               .limit(per_page) \
               .all()

    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'records': [r.to_dict() for r in records],
    }


def get_grading_detail(session, grading_id):
    """获取单条批改记录详情"""
    record = session.query(GradingRecord).filter_by(id=grading_id).first()
    if record:
        return record.to_dict()
    return None


def delete_grading(session, grading_id):
    """删除一条批改记录"""
    record = session.query(GradingRecord).filter_by(id=grading_id).first()
    if record:
        session.delete(record)
        session.commit()
        return True
    return False


def get_statistics(session):
    """获取统计数据"""
    from sqlalchemy import func
    total_gradings = session.query(func.count(GradingRecord.id)).scalar()
    total_homeworks = session.query(func.count(Homework.id)).scalar()
    avg_percentage = session.query(func.avg(GradingRecord.percentage)).scalar()

    return {
        'total_gradings': total_gradings or 0,
        'total_homeworks': total_homeworks or 0,
        'avg_percentage': round(avg_percentage or 0, 2),
    }

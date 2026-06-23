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
    uploader_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # 上传者；null=教师现批现改/历史数据

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


"""
* User class
* 用户账号ORM模型，映射users表，存储教师/学生账号（密码明文，仅用于课程项目演示）
* create by 林文光
* copyright USTC
* 2026.06.22
"""
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)  # 明文存储，未做哈希（课程项目简化）
    role = Column(String(16), nullable=False)       # 'teacher' / 'student'
    display_name = Column(String(64))
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'display_name': self.display_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


"""
* Assignment class
* 作业ORM模型，映射assignments表，存储教师发布的"作业"（持久化的标准答案集合）
* create by 林文光
* copyright USTC
* 2026.06.22
"""
class Assignment(Base):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    teacher_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    questions_json = Column(Text, default='[]')   # 标准答案JSON: [{number,type,answer,points}, ...]
    status = Column(String(16), default='active')  # 'active' / 'closed'
    created_at = Column(DateTime, default=datetime.now)

    submissions = relationship('Submission', back_populates='assignment',
                               cascade='all, delete-orphan')

    def to_dict(self, include_questions=True):
        import json
        questions = json.loads(self.questions_json or '[]')
        d = {
            'id': self.id,
            'name': self.name,
            'teacher_id': self.teacher_id,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'question_count': len(questions),
        }
        if include_questions:
            d['questions'] = questions
        return d


"""
* Submission class
* 提交ORM模型，映射submissions表，记录学生对某作业的一次提交及其审核状态
* create by 林文光
* copyright USTC
* 2026.06.22
"""
class Submission(Base):
    __tablename__ = 'submissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    grading_id = Column(Integer, ForeignKey('grading_records.id'), nullable=True)
    status = Column(String(16), default='pending')  # 'pending' / 'published'
    submitted_at = Column(DateTime, default=datetime.now)
    published_at = Column(DateTime, nullable=True)

    assignment = relationship('Assignment', back_populates='submissions')
    student = relationship('User')
    grading = relationship('GradingRecord')

    def to_dict(self, include_grading=False):
        d = {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'assignment_name': self.assignment.name if self.assignment else None,
            'student_id': self.student_id,
            'student_name': self.student.display_name if self.student else None,
            'grading_id': self.grading_id,
            'status': self.status,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
                            if self.submitted_at else None,
            'published_at': self.published_at.strftime('%Y-%m-%d %H:%M:%S')
                            if self.published_at else None,
        }
        if include_grading and self.grading:
            d['grading'] = self.grading.to_dict()
        return d


# ============ 数据库操作 ============

def init_db():
    """初始化数据库表，并对老库做轻量迁移与种子账号"""
    Base.metadata.create_all(engine)
    _migrate_schema(engine)
    _seed_default_users()


def _migrate_schema(eng):
    """对已存在的老表补充新增列（create_all 不会迁移已有表）"""
    from sqlalchemy import text
    with eng.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(homeworks)")).fetchall()
        col_names = [r[1] for r in rows]
        if col_names and 'uploader_id' not in col_names:
            conn.execute(text("ALTER TABLE homeworks ADD COLUMN uploader_id INTEGER"))


def _seed_default_users():
    """首次启动若无教师账号，插入默认教师 teacher/teacher"""
    session = Session()
    try:
        if not session.query(User).filter_by(role='teacher').first():
            session.add(User(
                username='teacher',
                password='teacher',
                role='teacher',
                display_name='默认教师',
            ))
            session.commit()
    finally:
        session.close()


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


# ============ 用户操作 ============

def get_user_by_credentials(session, username, password):
    """按用户名+密码查询用户（密码明文比对）"""
    return session.query(User).filter_by(
        username=username, password=password).first()


def get_user_by_id(session, user_id):
    """按 id 查询用户"""
    return session.query(User).filter_by(id=user_id).first()


def create_user(session, username, password, role, display_name=None):
    """新建用户，返回 User 实例；用户名重复时抛 IntegrityError"""
    user = User(
        username=username,
        password=password,
        role=role,
        display_name=display_name or username,
    )
    session.add(user)
    session.commit()
    return user


def list_users(session, role=None):
    """列出用户，可按 role 过滤"""
    q = session.query(User)
    if role:
        q = q.filter_by(role=role)
    return q.order_by(User.id.asc()).all()


def delete_user(session, user_id):
    """删除用户（不允许删除最后一个教师账号）"""
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return False
    if user.role == 'teacher':
        teacher_count = session.query(User).filter_by(role='teacher').count()
        if teacher_count <= 1:
            return False
    session.delete(user)
    session.commit()
    return True


# ============ 作业操作 ============

def create_assignment(session, name, teacher_id, questions):
    """新建作业，questions 为 list[dict]"""
    import json
    a = Assignment(
        name=name,
        teacher_id=teacher_id,
        questions_json=json.dumps(questions, ensure_ascii=False),
    )
    session.add(a)
    session.commit()
    return a


def get_assignment(session, assignment_id):
    """按 id 查询作业"""
    return session.query(Assignment).filter_by(id=assignment_id).first()


def list_assignments(session, teacher_id=None, status=None):
    """列出作业，可按教师与状态过滤"""
    q = session.query(Assignment)
    if teacher_id is not None:
        q = q.filter_by(teacher_id=teacher_id)
    if status:
        q = q.filter_by(status=status)
    return q.order_by(Assignment.created_at.desc()).all()


def update_assignment(session, assignment_id, **fields):
    """更新作业的 name/status/questions（None 表示不修改）"""
    import json
    a = session.query(Assignment).filter_by(id=assignment_id).first()
    if not a:
        return None
    if fields.get('name') is not None:
        a.name = fields['name']
    if fields.get('status') is not None:
        a.status = fields['status']
    if fields.get('questions') is not None:
        a.questions_json = json.dumps(fields['questions'], ensure_ascii=False)
    session.commit()
    return a


def delete_assignment(session, assignment_id):
    """删除作业"""
    a = session.query(Assignment).filter_by(id=assignment_id).first()
    if not a:
        return False
    session.delete(a)
    session.commit()
    return True


# ============ 提交操作 ============

def create_submission(session, assignment_id, student_id, grading_id,
                      status='pending'):
    """新建提交记录"""
    sub = Submission(
        assignment_id=assignment_id,
        student_id=student_id,
        grading_id=grading_id,
        status=status,
    )
    session.add(sub)
    session.commit()
    return sub


def get_submission(session, submission_id):
    """按 id 查询提交"""
    return session.query(Submission).filter_by(id=submission_id).first()


def list_submissions(session, assignment_id=None, student_id=None,
                     status=None, page=1, per_page=20):
    """列出提交，支持按作业/学生/状态过滤与分页"""
    q = session.query(Submission)
    if assignment_id is not None:
        q = q.filter_by(assignment_id=assignment_id)
    if student_id is not None:
        q = q.filter_by(student_id=student_id)
    if status:
        q = q.filter_by(status=status)

    total = q.count()
    rows = q.order_by(Submission.submitted_at.desc()) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()
    return {
        'total': total,
        'page': page,
        'per_page': per_page,
        'submissions': [r.to_dict(include_grading=True) for r in rows],
    }


def publish_submission(session, submission_id):
    """发布提交：pending → published，记发布时间"""
    sub = session.query(Submission).filter_by(id=submission_id).first()
    if not sub:
        return None
    sub.status = 'published'
    sub.published_at = datetime.now()
    session.commit()
    return sub


def update_question_results(session, grading_id, overrides):
    """按题号覆盖批改得分/对错，并重算总分。overrides: {number: {earned_points, is_correct}}"""
    from sqlalchemy import func
    record = session.query(GradingRecord).filter_by(id=grading_id).first()
    if not record:
        return None
    for qr in record.question_results:
        ov = overrides.get(qr.question_number)
        if not ov:
            continue
        if ov.get('is_correct') is not None:
            qr.is_correct = bool(ov['is_correct'])
        if ov.get('earned_points') is not None:
            qr.earned_points = float(ov['earned_points'])
    # 重算总分
    record.earned_points = sum(qr.earned_points for qr in record.question_results)
    record.total_points = sum(qr.total_points for qr in record.question_results)
    record.percentage = round(
        record.earned_points / record.total_points * 100, 2
    ) if record.total_points else 0
    session.commit()
    return record

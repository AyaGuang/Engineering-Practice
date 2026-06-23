"""
* QuestionResultRecord class
* Flask后端 - 提供OCR识别与批改API
* create by 廖帅
* copyright USTC
* 2026.02.22
"""
import os
import json
import uuid
import logging
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError

import config
import settings_store
from core import preprocessor, ocr_engine, parser, grader, exporter
from core.llm_corrector import LLMCorrector
from models.question import Question, QuestionType
import database as db

# 配置日志：同时输出到控制台和文件
_log_format = '[%(asctime)s] %(levelname)s %(name)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=_log_format,
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), 'app.log'),
            encoding='utf-8',
        ),
    ],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# 初始化数据库
db.init_db()

# 启动时加载用户配置覆盖默认LLM设置
def _apply_user_settings():
    """从用户配置文件加载并覆盖config中的LLM配置"""
    saved = settings_store.load_settings()
    if saved.get('api_key'):
        config.LLM_API_KEY = saved['api_key']
    if saved.get('base_url'):
        config.LLM_BASE_URL = saved['base_url']
    if saved.get('model'):
        config.LLM_MODEL = saved['model']
    if saved.get('timeout'):
        config.LLM_TIMEOUT = int(saved['timeout'])
    logger.info('LLM配置: model=%s, base_url=%s, has_key=%s',
                config.LLM_MODEL, config.LLM_BASE_URL or '(default)',
                bool(config.LLM_API_KEY))

_apply_user_settings()

# 启动时清理过期上传文件（默认7天前），避免磁盘无限堆积
def _cleanup_expired_uploads(max_age_days=7):
    import time
    import glob
    now = time.time()
    cutoff = now - max_age_days * 86400
    for f in glob.glob(os.path.join(config.UPLOAD_FOLDER, '*')):
        try:
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
        except OSError:
            pass

_cleanup_expired_uploads()

# LLM纠错实例（延迟初始化）
_llm_corrector = None


def _get_llm_corrector():
    """获取或创建LLM纠错实例。配置变更后调用方应先重置。"""
    global _llm_corrector
    if _llm_corrector is None and config.LLM_API_KEY:
        _llm_corrector = LLMCorrector(
            api_key=config.LLM_API_KEY,
            model=config.LLM_MODEL,
            base_url=config.LLM_BASE_URL or None,
            timeout=config.LLM_TIMEOUT,
        )
    return _llm_corrector


def _reset_llm_corrector():
    """重置LLM实例（配置变更后调用，下次使用时重建）"""
    global _llm_corrector
    _llm_corrector = None


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def _current_user_id():
    """从请求头读取当前用户 id（简单身份机制，无 token）"""
    raw = request.headers.get('X-User-Id')
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _current_user():
    """返回当前 User 对象，查不到返回 None。注意返回的对象已脱离 session，
    仅可访问已加载的标量字段（id/role/username/display_name）。"""
    uid = _current_user_id()
    if uid is None:
        return None
    session = db.get_session()
    try:
        return db.get_user_by_id(session, uid)
    finally:
        session.close()


def _require_teacher():
    """校验当前用户是教师。返回 (user, error) 元组：通过时 user 非空、error 为 None；
    否则 user 为 None、error 为 (response, status)。"""
    user = _current_user()
    if user is None:
        return None, (jsonify({"error": "未登录或身份无效"}), 401)
    if user.role != 'teacher':
        return None, (jsonify({"error": "需要教师权限"}), 403)
    return user, None


# ============ API路由 ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行中"})


# ============ 认证与账号 API ============

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """账号密码登录，返回用户身份与角色（密码明文比对）"""
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({"ok": False, "error": "请输入账号和密码"}), 400
    session = db.get_session()
    try:
        user = db.get_user_by_credentials(session, username, password)
    finally:
        session.close()
    if not user:
        return jsonify({"ok": False, "error": "账号或密码错误"}), 200
    logger.info('用户登录: %s (role=%s)', user.username, user.role)
    return jsonify({
        "ok": True,
        "user_id": user.id,
        "role": user.role,
        "username": user.username,
        "display_name": user.display_name,
    })


@app.route('/api/users', methods=['GET'])
def list_users_api():
    """列出账号（教师权限）。不传 role 时列全部，传 student/teacher 则过滤"""
    _, err = _require_teacher()
    if err:
        return err
    role = request.args.get('role')  # None = 全部
    session = db.get_session()
    try:
        users = db.list_users(session, role=role)
        return jsonify({"users": [u.to_dict() for u in users]})
    finally:
        session.close()


@app.route('/api/users', methods=['POST'])
def create_user_api():
    """新建账号（教师权限）"""
    user, err = _require_teacher()
    if err:
        return err
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', 'student')
    display_name = (data.get('display_name') or '').strip() or username
    if not username or not password:
        return jsonify({"error": "账号和密码不能为空"}), 400
    if role not in ('teacher', 'student'):
        return jsonify({"error": "角色非法"}), 400
    session = db.get_session()
    try:
        try:
            db.create_user(session, username, password, role, display_name)
        except IntegrityError:
            return jsonify({"error": "账号已存在"}), 400
    finally:
        session.close()
    logger.info('新建账号: %s (role=%s) by %s', username, role, user.username)
    return jsonify({"message": "创建成功"})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user_api(user_id):
    """删除账号（教师权限）"""
    user, err = _require_teacher()
    if err:
        return err
    if user_id == user.id:
        return jsonify({"error": "不能删除当前登录账号"}), 400
    session = db.get_session()
    try:
        ok = db.delete_user(session, user_id)
    finally:
        session.close()
    if not ok:
        return jsonify({"error": "删除失败（账号不存在或最后一个教师账号）"}), 400
    return jsonify({"message": "删除成功"})


# ============ 作业 API ============

@app.route('/api/assignments', methods=['GET'])
def list_assignments_api():
    """列出作业（教师权限，仅本人）"""
    user, err = _require_teacher()
    if err:
        return err
    status = request.args.get('status')
    session = db.get_session()
    try:
        items = db.list_assignments(session, teacher_id=user.id, status=status)
        return jsonify({"assignments": [a.to_dict() for a in items]})
    finally:
        session.close()


@app.route('/api/assignments', methods=['POST'])
def create_assignment_api():
    """新建作业（教师权限）"""
    user, err = _require_teacher()
    if err:
        return err
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    questions = data.get('questions', [])
    if not name:
        return jsonify({"error": "作业名不能为空"}), 400
    if not isinstance(questions, list):
        return jsonify({"error": "questions 必须为数组"}), 400
    session = db.get_session()
    try:
        a = db.create_assignment(session, name, user.id, questions)
        result = a.to_dict()   # 必须在 session 关闭前取值
    finally:
        session.close()
    logger.info('新建作业: %s (%d题) by %s', name, len(questions), user.username)
    return jsonify({"message": "创建成功", "assignment": result})


@app.route('/api/assignments/active', methods=['GET'])
def list_active_assignments_api():
    """学生视角：列出所有 active 作业（不返回标准答案）"""
    user = _current_user()
    if user is None:
        return jsonify({"error": "未登录"}), 401
    session = db.get_session()
    try:
        items = db.list_assignments(session, status='active')
        return jsonify({"assignments": [a.to_dict(include_questions=False)
                                       for a in items]})
    finally:
        session.close()


@app.route('/api/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment_api(assignment_id):
    """作业详情（教师仅本人可查，含标准答案）"""
    user, err = _require_teacher()
    if err:
        return err
    session = db.get_session()
    try:
        a = db.get_assignment(session, assignment_id)
        if not a or a.teacher_id != user.id:
            return jsonify({"error": "作业不存在"}), 404
        return jsonify({"assignment": a.to_dict()})
    finally:
        session.close()


@app.route('/api/assignments/<int:assignment_id>', methods=['PUT'])
def update_assignment_api(assignment_id):
    """更新作业名称/状态/标准答案（教师权限）"""
    user, err = _require_teacher()
    if err:
        return err
    data = request.get_json() or {}
    session = db.get_session()
    try:
        a = db.get_assignment(session, assignment_id)
        if not a or a.teacher_id != user.id:
            return jsonify({"error": "作业不存在"}), 404
        a = db.update_assignment(
            session, assignment_id,
            name=data.get('name'),
            status=data.get('status'),
            questions=data.get('questions'),
        )
        result = a.to_dict()
    finally:
        session.close()
    return jsonify({"message": "已更新", "assignment": result})


@app.route('/api/assignments/<int:assignment_id>', methods=['DELETE'])
def delete_assignment_api(assignment_id):
    """删除作业（教师权限）"""
    user, err = _require_teacher()
    if err:
        return err
    session = db.get_session()
    try:
        a = db.get_assignment(session, assignment_id)
        if not a or a.teacher_id != user.id:
            return jsonify({"error": "作业不存在"}), 404
        db.delete_assignment(session, assignment_id)
    finally:
        session.close()
    return jsonify({"message": "已删除"})


@app.route('/api/upload', methods=['POST'])
def upload_image():
    """上传作业图片，返回文件ID，并存入数据库"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到上传文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "不支持的文件格式"}), 400

    # 生成唯一文件名保存
    ext = file.filename.rsplit('.', 1)[1].lower()
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    # 存入数据库
    session = db.get_session()
    try:
        db.save_homework(session, file_id, file.filename, filename, filepath)
    finally:
        session.close()

    return jsonify({
        "file_id": file_id,
        "filename": filename,
        "message": "上传成功"
    })


@app.route('/api/preprocess/<file_id>', methods=['POST'])
def preprocess_image(file_id):
    """图像预处理"""
    filepath = _find_file(file_id)
    if not filepath:
        return jsonify({"error": "文件不存在"}), 404

    try:
        processed = preprocessor.preprocess(filepath)
        import cv2
        processed_path = os.path.join(config.UPLOAD_FOLDER, f"{file_id}_processed.png")
        cv2.imwrite(processed_path, processed)
        return jsonify({"message": "预处理完成", "file_id": file_id})
    except Exception as e:
        logger.error('预处理失败:\n%s', traceback.format_exc())
        return jsonify({"error": f"预处理失败: {str(e)}"}), 500


@app.route('/api/ocr/<file_id>', methods=['POST'])
def ocr_recognize(file_id):
    """OCR识别"""
    filepath = _find_file(file_id)
    if not filepath:
        return jsonify({"error": "文件不存在"}), 404

    try:
        results = ocr_engine.recognize(filepath)
        ocr_data = [
            {
                "bbox": r.bbox,
                "text": r.text,
                "confidence": round(r.confidence, 4)
            }
            for r in results
        ]
        return jsonify({"ocr_results": ocr_data, "count": len(ocr_data)})
    except Exception as e:
        logger.error('OCR识别失败:\n%s', traceback.format_exc())
        return jsonify({"error": f"OCR识别失败: {str(e)}"}), 500


@app.route('/api/parse', methods=['POST'])
def parse_ocr_results():
    """解析OCR结果为题号-答案对"""
    data = request.get_json()
    if not data or 'ocr_results' not in data:
        return jsonify({"error": "缺少ocr_results参数"}), 400

    from models.question import OcrResult
    ocr_results = [
        OcrResult(bbox=r['bbox'], text=r['text'], confidence=r['confidence'])
        for r in data['ocr_results']
    ]

    parsed = parser.parse_answers(ocr_results)
    return jsonify({"parsed_answers": {str(k): v for k, v in parsed.items()}})


def _run_grading_pipeline(filepath, questions_data,
                          override_llm=None, override_match_mode=None,
                          override_enhance=None):
    """执行 OCR→LLM纠错→解析→批改 流水线。
    返回 (report, parsed_display, ocr_results, llm_status, llm_count)。
    override_* 为 None 时回退到持久化设置。"""
    _cfg = settings_store.load_settings()
    enable_correction = override_llm if override_llm is not None \
        else _cfg.get('enable_llm_correction', False)
    match_mode = override_match_mode or _cfg.get('match_mode', 'by_number')
    enhance_choice = override_enhance if override_enhance is not None \
        else _cfg.get('enhance_choice', False)

    questions = []
    for q in questions_data:
        try:
            q_type = QuestionType(q['type'])
        except (ValueError, KeyError):
            q_type = QuestionType.FILL_BLANK
        questions.append(Question(
            number=q.get('number', 0),
            q_type=q_type,
            standard_answer=q.get('answer', ''),
            points=q.get('points', 1.0),
            accept_alternatives=q.get('alternatives', [])
        ))

    ocr_results = ocr_engine.recognize(filepath)
    logger.info('OCR识别完成, %d条结果', len(ocr_results))

    llm_status = None
    llm_count = 0
    llm_matched = {}
    if enable_correction:
        corrector = _get_llm_corrector()
        if corrector:
            ocr_results, llm_count, llm_matched = corrector.correct(
                ocr_results, questions=questions_data)
            llm_status = 'applied'
            logger.info('LLM纠错完成, 修正%d处, 匹配%d题',
                        llm_count, len(llm_matched))
        else:
            llm_status = 'no_api_key'

    if llm_matched:
        parsed = {int(k) if str(k).isdigit() else k: v
                  for k, v in llm_matched.items()}
        report = grader.grade_all(parsed, questions)
    elif match_mode == 'by_position':
        parsed_list = parser.parse_answers_by_position(
            ocr_results, skip_options=enhance_choice)
        parsed = {qnum: ans for qnum, ans in parsed_list}
        report = grader.grade_by_position(parsed_list, questions)
    else:
        parsed = parser.parse_answers(ocr_results, skip_options=enhance_choice)
        report = grader.grade_all(parsed, questions)

    logger.info('批改完成(模式:%s, 增强:%s), 得分%.1f/%.1f (%.1f%%)',
                match_mode, enhance_choice, report.earned_points,
                report.total_points, report.percentage)
    return report, parsed, ocr_results, llm_status, llm_count


def _build_result_and_summary(report):
    """从 GradingReport 构建响应用 result_data 与 summary"""
    result_data = []
    for r in report.results:
        result_data.append({
            "number": r.question.number,
            "type": r.question.q_type.value,
            "type_name": r.question.q_type.display_name,
            "recognized_text": r.recognized_text,
            "standard_answer": r.question.standard_answer,
            "is_correct": r.is_correct,
            "match_score": round(r.match_score, 4),
            "earned_points": r.earned_points,
            "total_points": r.question.points,
        })
    summary = {
        "total_points": report.total_points,
        "earned_points": report.earned_points,
        "percentage": round(report.percentage, 2),
    }
    return result_data, summary


@app.route('/api/grade', methods=['POST'])
def grade_homework():
    """批改作业 - 核心接口，支持一步完成OCR+批改，并存入数据库"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "缺少请求数据"}), 400

    file_id = data.get('file_id')
    questions_data = data.get('questions', [])
    if not file_id or not questions_data:
        return jsonify({"error": "缺少file_id或questions参数"}), 400

    filepath = _find_file(file_id)
    if not filepath:
        return jsonify({"error": "文件不存在"}), 404

    try:
        logger.info('开始批改 file_id=%s, %d道题', file_id, len(questions_data))
        report, parsed, ocr_results, llm_status, llm_count = _run_grading_pipeline(
            filepath, questions_data,
            override_llm=data.get('enable_llm_correction'),
            override_match_mode=data.get('match_mode'),
            override_enhance=data.get('enhance_choice'))
        result_data, summary = _build_result_and_summary(report)

        # 存入数据库
        session = db.get_session()
        try:
            homework = db.get_homework_by_file_id(session, file_id)
            if homework:
                grading_record = db.save_grading(
                    session, homework, result_data, summary, len(ocr_results))
                grading_id = grading_record.id
            else:
                grading_id = None
        finally:
            session.close()

        ocr_data = [
            {
                "bbox": r.bbox,
                "text": r.text,
                "confidence": round(r.confidence, 4)
            }
            for r in ocr_results
        ]

        return jsonify({
            "results": result_data,
            "summary": summary,
            "ocr_count": len(ocr_results),
            "ocr_results": ocr_data,
            "parsed_answers": {str(k): v for k, v in parsed.items()},
            "grading_id": grading_id,
            "llm_correction": {
                "status": llm_status,
                "corrected_count": llm_count,
            },
        })

    except Exception as e:
        logger.error('批改失败:\n%s', traceback.format_exc())
        return jsonify({"error": f"批改失败: {str(e)}"}), 500


# ============ 提交 API（学生提交 / 审核流转） ============

@app.route('/api/submissions', methods=['POST'])
def create_submission_api():
    """学生提交作业：自动OCR批改 → 建/更新 Homework.uploader_id + GradingRecord
    + Submission(status=pending)，返回预览"""
    user = _current_user()
    if user is None:
        return jsonify({"error": "未登录"}), 401
    if user.role != 'student':
        return jsonify({"error": "仅学生可提交作业"}), 403

    data = request.get_json() or {}
    assignment_id = data.get('assignment_id')
    file_id = data.get('file_id')
    if not assignment_id or not file_id:
        return jsonify({"error": "缺少 assignment_id 或 file_id"}), 400

    filepath = _find_file(file_id)
    if not filepath:
        return jsonify({"error": "上传文件不存在，请重新上传"}), 404

    # 取作业标准答案（学生端不可见，但服务端批改需要）
    session = db.get_session()
    try:
        a = db.get_assignment(session, int(assignment_id))
        if not a or a.status != 'active':
            return jsonify({"error": "作业不存在或已关闭"}), 404
        questions = a.to_dict()['questions']
        assignment_id_int = a.id
    finally:
        session.close()

    try:
        logger.info('学生提交: assignment=%s student=%s', assignment_id_int, user.username)
        report, parsed, ocr_results, llm_status, llm_count = _run_grading_pipeline(
            filepath, questions, override_llm=data.get('enable_llm_correction'))
        result_data, summary = _build_result_and_summary(report)

        session = db.get_session()
        try:
            hw = db.get_homework_by_file_id(session, file_id)
            if hw is None:
                session.close()
                return jsonify({"error": "上传记录不存在，请重新上传图片"}), 404
            hw.uploader_id = user.id  # 标记上传者
            grading = db.save_grading(session, hw, result_data, summary,
                                      len(ocr_results))
            sub = db.create_submission(session, assignment_id_int, user.id,
                                       grading.id, 'pending')
            preview = sub.to_dict(include_grading=True)
        finally:
            session.close()

        logger.info('提交完成 submission=%s 得分%.1f%%',
                    sub.id, summary.get('percentage', 0))
        ocr_data = [
            {"bbox": r.bbox, "text": r.text,
             "confidence": round(r.confidence, 4)}
            for r in ocr_results
        ]
        return jsonify({
            "message": "提交成功，等待教师审核",
            "submission": preview,
            "results": result_data,
            "summary": summary,
            "ocr_count": len(ocr_results),
            "ocr_results": ocr_data,
            "parsed_answers": {str(k): v for k, v in parsed.items()},
            "llm_correction": {"status": llm_status, "corrected_count": llm_count},
        })

    except Exception as e:
        logger.error('学生提交失败:\n%s', traceback.format_exc())
        return jsonify({"error": f"提交失败: {str(e)}"}), 500


@app.route('/api/submissions', methods=['GET'])
def list_submissions_api():
    """列出提交：教师按 assignment_id 列全部；学生强制仅列本人"""
    user = _current_user()
    if user is None:
        return jsonify({"error": "未登录"}), 401

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    session = db.get_session()
    try:
        if user.role == 'teacher':
            assignment_id = request.args.get('assignment_id', type=int)
            result = db.list_submissions(
                session, assignment_id=assignment_id,
                status=status, page=page, per_page=per_page)
        else:
            result = db.list_submissions(
                session, student_id=user.id,
                status=status, page=page, per_page=per_page)
    finally:
        session.close()
    return jsonify(result)


@app.route('/api/submissions/<int:submission_id>', methods=['GET'])
def get_submission_api(submission_id):
    """提交详情：教师可见全部；学生仅当 status=published 或本人可见"""
    user = _current_user()
    if user is None:
        return jsonify({"error": "未登录"}), 401

    session = db.get_session()
    try:
        sub = db.get_submission(session, submission_id)
        if not sub:
            return jsonify({"error": "提交不存在"}), 404
        if user.role == 'student':
            if sub.student_id != user.id and sub.status != 'published':
                return jsonify({"error": "无权查看"}), 403
        result = sub.to_dict(include_grading=True)
    finally:
        session.close()
    return jsonify({"submission": result})


@app.route('/api/submissions/<int:submission_id>/results', methods=['PUT'])
def update_submission_results_api(submission_id):
    """教师手动改分：按题号覆盖 earned_points/is_correct，并重算总分。
    请求体 {results: [{number, earned_points?, is_correct?}]}"""
    user, err = _require_teacher()
    if err:
        return err
    data = request.get_json() or {}
    raw_results = data.get('results', [])
    if not isinstance(raw_results, list):
        return jsonify({"error": "results 必须为数组"}), 400

    overrides = {}
    for r in raw_results:
        if not isinstance(r, dict) or r.get('number') is None:
            continue
        overrides[r['number']] = {
            'earned_points': r.get('earned_points'),
            'is_correct': r.get('is_correct'),
        }
    if not overrides:
        return jsonify({"error": "没有有效的改分项"}), 400

    session = db.get_session()
    try:
        sub = db.get_submission(session, submission_id)
        if not sub:
            return jsonify({"error": "提交不存在"}), 404
        if sub.grading_id is None:
            return jsonify({"error": "该提交无批改记录，无法改分"}), 400
        grading = db.update_question_results(session, sub.grading_id, overrides)
        if grading is None:
            return jsonify({"error": "批改记录不存在"}), 404
        result = sub.to_dict(include_grading=True)
    finally:
        session.close()
    logger.info('教师改分: submission=%s by %s -> %.1f%%',
                submission_id, user.username,
                result['grading']['percentage'] if result.get('grading') else 0)
    return jsonify({"message": "改分成功", "submission": result})


@app.route('/api/submissions/<int:submission_id>/publish', methods=['POST'])
def publish_submission_api(submission_id):
    """教师发布提交：pending → published"""
    user, err = _require_teacher()
    if err:
        return err
    session = db.get_session()
    try:
        sub = db.get_submission(session, submission_id)
        if not sub:
            return jsonify({"error": "提交不存在"}), 404
        sub = db.publish_submission(session, submission_id)
        result = sub.to_dict(include_grading=True)
    finally:
        session.close()
    logger.info('教师发布: submission=%s by %s', submission_id, user.username)
    return jsonify({"message": "已发布", "submission": result})


@app.route('/api/export/<file_id>', methods=['POST'])
def export_report(file_id):
    """导出批改报告"""
    data = request.get_json()
    if not data or 'results' not in data:
        return jsonify({"error": "缺少results参数"}), 400

    fmt = data.get('format', 'csv')
    report = _build_report_from_data(data['results'])

    export_path = os.path.join(config.UPLOAD_FOLDER, f"{file_id}_report.{fmt}")

    try:
        if fmt == 'csv':
            exporter.export_csv(report, export_path)
        elif fmt == 'html':
            exporter.export_html(report, export_path)
        else:
            return jsonify({"error": "不支持的导出格式"}), 400

        with open(export_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"content": content, "format": fmt})
    except Exception as e:
        logger.error('导出失败:\n%s', traceback.format_exc())
        return jsonify({"error": f"导出失败: {str(e)}"}), 500


# ============ 历史记录API ============

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    查询批改历史记录，支持多条件检索。
    参数:
      keyword  - 按文件名模糊搜索
      date_from - 起始日期 (YYYY-MM-DD)
      date_to   - 结束日期 (YYYY-MM-DD)
      min_score - 最低得分率
      max_score - 最高得分率
      page      - 页码 (默认1)
      per_page  - 每页条数 (默认20)
    """
    from datetime import datetime

    keyword = request.args.get('keyword', None)
    date_from = request.args.get('date_from', None)
    date_to = request.args.get('date_to', None)
    min_score = request.args.get('min_score', None, type=float)
    max_score = request.args.get('max_score', None, type=float)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 解析日期
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
        except ValueError:
            date_from = None
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59)
        except ValueError:
            date_to = None

    session = db.get_session()
    try:
        result = db.query_history(
            session, keyword=keyword, date_from=date_from, date_to=date_to,
            min_score=min_score, max_score=max_score, page=page, per_page=per_page)
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/history/<int:grading_id>', methods=['GET'])
def get_history_detail(grading_id):
    """获取单条批改记录详情"""
    session = db.get_session()
    try:
        detail = db.get_grading_detail(session, grading_id)
        if detail:
            return jsonify(detail)
        return jsonify({"error": "记录不存在"}), 404
    finally:
        session.close()


@app.route('/api/history/<int:grading_id>', methods=['DELETE'])
def delete_history(grading_id):
    """删除一条批改记录"""
    session = db.get_session()
    try:
        if db.delete_grading(session, grading_id):
            return jsonify({"message": "删除成功"})
        return jsonify({"error": "记录不存在"}), 404
    finally:
        session.close()


@app.route('/api/statistics', methods=['GET'])
def get_stats():
    """获取统计数据"""
    session = db.get_session()
    try:
        stats = db.get_statistics(session)
        return jsonify(stats)
    finally:
        session.close()


# ============ 设置API ============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """读取配置（API Key脱敏返回）"""
    saved = settings_store.load_settings()
    return jsonify({
        'api_key': saved.get('api_key', ''),
        'api_key_set': bool(saved.get('api_key')),
        'base_url': saved.get('base_url', ''),
        'model': saved.get('model', 'gpt-4o-mini'),
        'timeout': saved.get('timeout', 30),
        'enable_llm_correction': saved.get('enable_llm_correction', False),
        'match_mode': saved.get('match_mode', 'by_number'),
        'enhance_choice': saved.get('enhance_choice', False),
    })


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """更新配置并持久化（LLM配置 + 批改选项）"""
    data = request.get_json() or {}
    # 以已有配置为base合并，避免None覆盖合法值
    current = settings_store.load_settings()

    # api_key=None 表示不修改，保留原值
    api_key = data.get('api_key')
    if api_key is None:
        api_key = current.get('api_key', '')
    elif isinstance(api_key, str):
        api_key = api_key.strip()
    else:
        api_key = ''

    def _str(key, default=''):
        v = data.get(key)
        return v.strip() if isinstance(v, str) else default

    settings = {
        'api_key': api_key,
        'base_url': _str('base_url', current.get('base_url', '')),
        'model': _str('model') or current.get('model', 'gpt-4o-mini'),
        'timeout': int(data.get('timeout') or current.get('timeout', 30)),
        'enable_llm_correction': bool(data.get('enable_llm_correction',
                                               current.get('enable_llm_correction', False))),
        'match_mode': data.get('match_mode') or current.get('match_mode', 'by_number'),
        'enhance_choice': bool(data.get('enhance_choice',
                                        current.get('enhance_choice', False))),
    }
    try:
        settings_store.save_settings(settings)
    except OSError as e:
        return jsonify({"error": f"保存失败: {str(e)}"}), 500

    # 覆盖运行时config并重置纠错实例
    config.LLM_API_KEY = settings['api_key']
    config.LLM_BASE_URL = settings['base_url']
    config.LLM_MODEL = settings['model']
    config.LLM_TIMEOUT = settings['timeout']
    _reset_llm_corrector()
    logger.info('配置已更新: model=%s, base_url=%s, has_key=%s, '
                'ai_correction=%s, match_mode=%s, enhance_choice=%s',
                config.LLM_MODEL, config.LLM_BASE_URL or '(default)',
                bool(config.LLM_API_KEY),
                settings['enable_llm_correction'],
                settings['match_mode'], settings['enhance_choice'])
    return jsonify({"message": "设置已保存"})


@app.route('/api/settings/test', methods=['POST'])
def test_settings():
    """测试LLM连接是否正常。用提交的配置临时创建实例。"""
    data = request.get_json() or {}
    api_key = data.get('api_key', '').strip()
    base_url = data.get('base_url', '').strip() or None
    model = data.get('model', '').strip() or 'gpt-4o-mini'

    if not api_key:
        return jsonify({"ok": False, "error": "未填写API Key"}), 400

    try:
        tester = LLMCorrector(
            api_key=api_key, model=model, base_url=base_url, timeout=15)
        resp = tester.client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': '请回复"OK"'}],
            max_tokens=10,
            temperature=0,
        )
        reply = (resp.choices[0].message.content or '').strip()
        logger.info('LLM测试连接成功: model=%s, reply=%s', model, reply[:50])
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        logger.warning('LLM测试连接失败: %s', e)
        return jsonify({"ok": False, "error": str(e)}), 200


# ============ 辅助函数 ============

def _find_file(file_id):
    """根据file_id查找上传的文件"""
    for ext in config.ALLOWED_EXTENSIONS:
        path = os.path.join(config.UPLOAD_FOLDER, f"{file_id}.{ext}")
        if os.path.exists(path):
            return path
    return None


def _cleanup_files(file_id):
    """清理file_id相关的所有上传文件（原图、预处理图、报告等）"""
    import glob
    pattern = os.path.join(config.UPLOAD_FOLDER, f"{file_id}*")
    for f in glob.glob(pattern):
        try:
            os.remove(f)
        except OSError:
            pass


def _build_report_from_data(results_data):
    """从API数据重建GradingReport对象"""
    from models.result import QuestionResult, GradingReport
    results = []
    for r in results_data:
        try:
            q_type = QuestionType(r['type'])
        except (ValueError, KeyError):
            q_type = QuestionType.FILL_BLANK
        q = Question(
            number=r['number'],
            q_type=q_type,
            standard_answer=r['standard_answer'],
            points=r['total_points']
        )
        results.append(QuestionResult(
            question=q,
            recognized_text=r['recognized_text'],
            is_correct=r['is_correct'],
            match_score=r['match_score'],
            earned_points=r['earned_points'],
        ))
    return GradingReport(results=results)


if __name__ == '__main__':
    print(f"后端服务启动: http://{config.HOST}:{config.PORT}")
    print("API接口:")
    print("  GET  /api/health              - 健康检查")
    print("  POST /api/upload              - 上传图片")
    print("  POST /api/ocr/<file_id>       - OCR识别")
    print("  POST /api/grade               - 批改作业(核心)")
    print("  POST /api/export/<id>         - 导出报告")
    print("  GET  /api/history             - 查询批改历史")
    print("  GET  /api/history/<id>        - 查看批改详情")
    print("  DELETE /api/history/<id>      - 删除批改记录")
    print("  GET  /api/statistics          - 统计数据")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

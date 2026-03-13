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

from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from core import preprocessor, ocr_engine, parser, grader, exporter
from models.question import Question, QuestionType
import database as db

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# 初始化数据库
db.init_db()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


# ============ API路由 ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行中"})


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

    # 构建Question对象
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

    try:
        # 完整流水线：OCR识别 → 解析 → 批改
        ocr_results = ocr_engine.recognize(filepath)
        parsed = parser.parse_answers(ocr_results)
        report = grader.grade_all(parsed, questions)

        # 构建响应
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

        # 清理上传的图片文件，释放磁盘空间
        _cleanup_files(file_id)

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
        })

    except Exception as e:
        return jsonify({"error": f"批改失败: {str(e)}"}), 500


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

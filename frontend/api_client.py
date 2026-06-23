"""前端API客户端 - 通过HTTP调用后端服务"""
import requests
from typing import Optional

import config

BASE = config.API_BASE_URL


"""
* ApiClient class
* 后端API客户端封装，通过HTTP请求调用Flask后端的各项接口（上传、OCR、批改、导出、历史查询等）
* 使用 requests.Session 统一带 X-User-Id 身份头
* create by 林嘉晨
* copyright USTC
* 2026.02.01
"""
class ApiClient:

    def __init__(self, base_url: str = None):
        self.base_url = base_url or BASE
        self._session = requests.Session()
        self._user_id = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def set_current_user(self, user_id) -> None:
        """登录成功后调用：后续所有请求自动带 X-User-Id 头"""
        self._user_id = user_id
        if user_id is not None:
            self._session.headers.update({'X-User-Id': str(user_id)})
        else:
            self._session.headers.pop('X-User-Id', None)

    @property
    def user_id(self):
        return self._user_id

    # ---------- 健康检查 ----------

    def health_check(self) -> dict:
        """检查后端是否可用"""
        try:
            resp = self._session.get(self._url('/api/health'), timeout=5)
            return resp.json()
        except requests.ConnectionError:
            return {"status": "error", "message": "无法连接到后端服务"}

    # ---------- 认证与账号 ----------

    def login(self, username: str, password: str) -> dict:
        """账号密码登录"""
        try:
            resp = self._session.post(self._url('/api/auth/login'),
                                      json={'username': username,
                                            'password': password},
                                      timeout=10)
            return resp.json()
        except Exception as e:
            return {"ok": False, "error": f"无法连接服务: {e}"}

    def list_users(self, role: str = 'student') -> dict:
        """列出账号（教师权限）。role=None 表示不按角色过滤（列出全部）"""
        try:
            params = {} if role is None else {'role': role}
            resp = self._session.get(self._url('/api/users'),
                                     params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def create_user(self, username: str, password: str, role: str = 'student',
                    display_name: str = '') -> dict:
        """新建账号（教师权限）"""
        try:
            resp = self._session.post(self._url('/api/users'),
                                      json={'username': username,
                                            'password': password,
                                            'role': role,
                                            'display_name': display_name},
                                      timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def delete_user(self, user_id: int) -> dict:
        """删除账号（教师权限）"""
        try:
            resp = self._session.delete(self._url(f'/api/users/{user_id}'),
                                        timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ---------- 作业管理 ----------

    def list_assignments(self, status: str = None) -> dict:
        """列出本人作业（教师）"""
        try:
            params = {}
            if status:
                params['status'] = status
            resp = self._session.get(self._url('/api/assignments'),
                                     params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def list_active_assignments(self) -> dict:
        """学生视角：列出可提交作业（不含答案）"""
        try:
            resp = self._session.get(self._url('/api/assignments/active'),
                                     timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_assignment(self, assignment_id: int) -> dict:
        """作业详情（含答案，教师）"""
        try:
            resp = self._session.get(self._url(f'/api/assignments/{assignment_id}'),
                                     timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def create_assignment(self, name: str, questions: list) -> dict:
        """新建作业（教师）"""
        try:
            resp = self._session.post(self._url('/api/assignments'),
                                      json={'name': name,
                                            'questions': questions},
                                      timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_assignment(self, assignment_id: int, name: str = None,
                          status: str = None, questions: list = None) -> dict:
        """更新作业（教师）；None 字段不修改"""
        payload = {}
        if name is not None:
            payload['name'] = name
        if status is not None:
            payload['status'] = status
        if questions is not None:
            payload['questions'] = questions
        try:
            resp = self._session.put(self._url(f'/api/assignments/{assignment_id}'),
                                     json=payload, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def delete_assignment(self, assignment_id: int) -> dict:
        """删除作业（教师）"""
        try:
            resp = self._session.delete(
                self._url(f'/api/assignments/{assignment_id}'), timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ---------- 提交（学生提交 / 审核流转） ----------

    def submit_homework(self, assignment_id: int, file_id: str,
                        enable_llm_correction: bool = False) -> dict:
        """学生提交作业：自动批改并生成 pending 提交"""
        payload = {
            "assignment_id": assignment_id,
            "file_id": file_id,
            "enable_llm_correction": enable_llm_correction,
        }
        try:
            resp = self._session.post(self._url('/api/submissions'),
                                      json=payload, timeout=120)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def list_submissions(self, assignment_id: int = None, status: str = None,
                         page: int = 1, per_page: int = 20) -> dict:
        """列出提交：教师可传 assignment_id 列全部；学生仅列本人（后端强制）"""
        params = {'page': page, 'per_page': per_page}
        if assignment_id is not None:
            params['assignment_id'] = assignment_id
        if status:
            params['status'] = status
        try:
            resp = self._session.get(self._url('/api/submissions'),
                                     params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_submission(self, submission_id: int) -> dict:
        """提交详情（含 grading）；学生仅在 published 或本人时可见"""
        try:
            resp = self._session.get(self._url(f'/api/submissions/{submission_id}'),
                                     timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_submission_results(self, submission_id: int, results: list) -> dict:
        """教师改分：results=[{number, earned_points?, is_correct?}]"""
        try:
            resp = self._session.put(
                self._url(f'/api/submissions/{submission_id}/results'),
                json={'results': results}, timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def publish_submission(self, submission_id: int) -> dict:
        """教师发布提交：pending → published"""
        try:
            resp = self._session.post(
                self._url(f'/api/submissions/{submission_id}/publish'),
                timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ---------- 上传图片 ----------

    def upload_image(self, image_path: str) -> dict:
        """上传作业图片，返回file_id"""
        with open(image_path, 'rb') as f:
            files = {'file': (image_path.split('/')[-1], f)}
            resp = self._session.post(self._url('/api/upload'), files=files,
                                      timeout=30)
        if resp.status_code != 200:
            return {"error": resp.json().get("error", "上传失败")}
        return resp.json()

    # ---------- 预处理 ----------

    def preprocess(self, file_id: str) -> dict:
        """请求后端进行图像预处理"""
        resp = self._session.post(self._url(f'/api/preprocess/{file_id}'),
                                  timeout=60)
        return resp.json()

    # ---------- OCR识别 ----------

    def ocr_recognize(self, file_id: str) -> dict:
        """请求OCR识别"""
        resp = self._session.post(self._url(f'/api/ocr/{file_id}'),
                                  timeout=120)
        return resp.json()

    # ---------- 批改（核心接口） ----------

    def grade(self, file_id: str, questions: list,
              enable_llm_correction: bool = False) -> dict:
        """
        一步完成OCR+批改。
        questions: [{"number": 1, "type": "fill_blank", "answer": "北京", "points": 2}, ...]
        enable_llm_correction: 本次是否启用AI纠错（覆盖设置默认值）
        """
        payload = {
            "file_id": file_id,
            "questions": questions,
            "enable_llm_correction": enable_llm_correction,
        }
        resp = self._session.post(self._url('/api/grade'), json=payload,
                                  timeout=120)
        if resp.status_code != 200:
            return {"error": resp.json().get("error", "批改失败")}
        return resp.json()

    # ---------- 导出报告 ----------

    def export_report(self, file_id: str, results: list, fmt: str = 'csv') -> dict:
        """请求后端导出报告，返回报告内容"""
        payload = {
            "results": results,
            "format": fmt,
        }
        resp = self._session.post(self._url(f'/api/export/{file_id}'),
                                  json=payload, timeout=30)
        return resp.json()

    # ---------- 历史记录 ----------

    def get_history(self, **params) -> dict:
        """查询批改历史记录"""
        try:
            resp = self._session.get(self._url('/api/history'),
                                     params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_history_detail(self, grading_id: int) -> dict:
        """获取批改详情"""
        try:
            resp = self._session.get(self._url(f'/api/history/{grading_id}'),
                                     timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def delete_history(self, grading_id: int) -> dict:
        """删除批改记录"""
        try:
            resp = self._session.delete(self._url(f'/api/history/{grading_id}'),
                                        timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_statistics(self) -> dict:
        """获取统计数据"""
        try:
            resp = self._session.get(self._url('/api/statistics'), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    # ---------- 设置（LLM配置） ----------

    def get_settings(self) -> dict:
        """读取LLM配置"""
        try:
            resp = self._session.get(self._url('/api/settings'), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_settings(self, settings: dict) -> dict:
        """更新LLM配置"""
        try:
            resp = self._session.put(self._url('/api/settings'),
                                     json=settings, timeout=10)
            if resp.status_code != 200:
                return resp.json()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def test_settings(self, settings: dict) -> dict:
        """测试LLM连接"""
        try:
            resp = self._session.post(self._url('/api/settings/test'),
                                      json=settings, timeout=20)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

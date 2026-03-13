"""前端API客户端 - 通过HTTP调用后端服务"""
import requests
from typing import Optional

import config

BASE = config.API_BASE_URL


"""
* ApiClient class
* 后端API客户端封装，通过HTTP请求调用Flask后端的各项接口（上传、OCR、批改、导出、历史查询等）
* create by XXX
* copyright USTC
* 时间
"""
class ApiClient:

    def __init__(self, base_url: str = None):
        self.base_url = base_url or BASE

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ---------- 健康检查 ----------

    def health_check(self) -> dict:
        """检查后端是否可用"""
        try:
            resp = requests.get(self._url('/api/health'), timeout=5)
            return resp.json()
        except requests.ConnectionError:
            return {"status": "error", "message": "无法连接到后端服务"}

    # ---------- 上传图片 ----------

    def upload_image(self, image_path: str) -> dict:
        """上传作业图片，返回file_id"""
        with open(image_path, 'rb') as f:
            files = {'file': (image_path.split('/')[-1], f)}
            resp = requests.post(self._url('/api/upload'), files=files, timeout=30)
        if resp.status_code != 200:
            return {"error": resp.json().get("error", "上传失败")}
        return resp.json()

    # ---------- 预处理 ----------

    def preprocess(self, file_id: str) -> dict:
        """请求后端进行图像预处理"""
        resp = requests.post(self._url(f'/api/preprocess/{file_id}'), timeout=60)
        return resp.json()

    # ---------- OCR识别 ----------

    def ocr_recognize(self, file_id: str) -> dict:
        """请求OCR识别"""
        resp = requests.post(self._url(f'/api/ocr/{file_id}'), timeout=120)
        return resp.json()

    # ---------- 批改（核心接口） ----------

    def grade(self, file_id: str, questions: list) -> dict:
        """
        一步完成OCR+批改。
        questions: [{"number": 1, "type": "fill_blank", "answer": "北京", "points": 2}, ...]
        """
        payload = {
            "file_id": file_id,
            "questions": questions,
        }
        resp = requests.post(self._url('/api/grade'), json=payload, timeout=120)
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
        resp = requests.post(self._url(f'/api/export/{file_id}'), json=payload, timeout=30)
        return resp.json()

    # ---------- 历史记录 ----------

    def get_history(self, **params) -> dict:
        """查询批改历史记录"""
        try:
            resp = requests.get(self._url('/api/history'), params=params, timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_history_detail(self, grading_id: int) -> dict:
        """获取批改详情"""
        try:
            resp = requests.get(self._url(f'/api/history/{grading_id}'), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def delete_history(self, grading_id: int) -> dict:
        """删除批改记录"""
        try:
            resp = requests.delete(self._url(f'/api/history/{grading_id}'), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_statistics(self) -> dict:
        """获取统计数据"""
        try:
            resp = requests.get(self._url('/api/statistics'), timeout=10)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

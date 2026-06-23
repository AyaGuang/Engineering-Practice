"""
* SubmissionPanel class
* 学生提交作业面板：选择作业 → 上传图片 → 提交（自动批改）→ 显示待审核预览
* 复用 ImagePanel 做图片预览、ResultPanel 做批改预览
* create by 林文光
* copyright USTC
* 2026.06.23
"""
import os

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QSplitter,
                             QFileDialog, QMessageBox, QApplication,
                             QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

import config
from ui.image_panel import ImagePanel
from ui.result_panel import ResultPanel


"""
* SubmitWorker class
* 提交后台线程，在子线程中调用后端提交接口（含 OCR 批改），避免阻塞 UI
"""
class SubmitWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_client, assignment_id, file_id,
                 enable_llm_correction=False):
        super().__init__()
        self._api = api_client
        self._assignment_id = assignment_id
        self._file_id = file_id
        self._enable_llm = enable_llm_correction

    def run(self):
        try:
            result = self._api.submit_homework(
                self._assignment_id, self._file_id,
                enable_llm_correction=self._enable_llm)
            if 'error' in result:
                self.error.emit(result['error'])
            else:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SubmissionPanel(QWidget):
    """学生提交作业面板"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._file_id = None
        self._image_path = None
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("提交作业")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 顶部操作行：选作业 / 选图片 / AI纠错 / 提交
        ops = QHBoxLayout()
        ops.addWidget(QLabel("选择作业:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(220)
        ops.addWidget(self._combo, 1)

        self._cb_llm = QCheckBox("启用AI纠错")
        ops.addWidget(self._cb_llm)

        self._btn_image = QPushButton("选择图片")
        self._btn_image.clicked.connect(self._pick_image)
        ops.addWidget(self._btn_image)

        self._btn_submit = QPushButton("提交作业")
        self._btn_submit.clicked.connect(self._submit)
        ops.addWidget(self._btn_submit)

        layout.addLayout(ops)

        # 主区：左图片预览 | 右批改预览
        self._image_panel = ImagePanel()
        self._result_panel = ResultPanel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._image_panel)
        splitter.addWidget(self._result_panel)
        splitter.setSizes([550, 500])
        layout.addWidget(splitter, 1)

        # 状态条
        self._status = QLabel("请选择作业并上传作业图片")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("color:#555; padding:4px;")
        layout.addWidget(self._status)

    def showEvent(self, event):
        super().showEvent(event)
        # 延迟到下一轮事件循环再加载，避免在 show() 期间同步发 HTTP 请求
        # 卡住主线程、导致窗口画出框架后内容区空白。
        QTimer.singleShot(0, self._load_assignments)

    # ---------- 数据加载 ----------

    def _load_assignments(self):
        result = self._api.list_active_assignments()
        if 'error' in result:
            QMessageBox.warning(self, "加载作业失败", result['error'])
            return
        self._combo.clear()
        for a in result.get('assignments', []):
            label = f"{a.get('name', '')}（{a.get('question_count', 0)}题）"
            # 把 id 存到 userData
            self._combo.addItem(label, a.get('id'))
        if self._combo.count() == 0:
            self._status.setText("暂无可提交的作业（需教师先发布并开放作业）")
        else:
            self._status.setText("请选择作业并上传作业图片")

    def _current_assignment_id(self):
        idx = self._combo.currentIndex()
        if idx < 0:
            return None
        return self._combo.itemData(idx)

    # ---------- 选择图片 ----------

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择作业图片", "",
                                              config.IMAGE_FILTER)
        if not path:
            return
        self._image_path = path
        self._image_panel.set_image(path)
        self._status.setText(f"已加载图片：{os.path.basename(path)}，正在上传...")
        QApplication.processEvents()

        result = self._api.upload_image(path)
        if 'error' in result:
            self._file_id = None
            self._status.setText("上传失败")
            QMessageBox.warning(self, "上传失败", result['error'])
        else:
            self._file_id = result['file_id']
            self._status.setText(f"图片已上传，可点击「提交作业」")
            self._btn_submit.setFocus()

    # ---------- 提交 ----------

    def _submit(self):
        if self._worker is not None and self._worker.isRunning():
            return
        assignment_id = self._current_assignment_id()
        if assignment_id is None:
            QMessageBox.information(self, "提示", "请先选择一个作业")
            return
        if not self._file_id:
            QMessageBox.information(self, "提示", "请先选择并上传作业图片")
            return

        self._btn_submit.setEnabled(False)
        self._status.setText("正在识别与批改，请稍候...")
        QApplication.processEvents()

        self._worker = SubmitWorker(
            self._api, assignment_id, self._file_id,
            enable_llm_correction=self._cb_llm.isChecked())
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result):
        self._btn_submit.setEnabled(True)
        results = result.get('results', [])
        summary = result.get('summary', {})
        ocr_results = result.get('ocr_results', [])

        self._image_panel.set_ocr_results(ocr_results)
        self._result_panel.display_from_api(results, summary)

        pct = summary.get('percentage', 0)
        llm = result.get('llm_correction', {})
        extra = ""
        if llm.get('status') == 'applied':
            extra = f" | AI纠错修正{llm.get('corrected_count', 0)}处"
        self._status.setText(
            f"已提交，等待教师审核（预览得分 {pct:.1f}%）{extra}")
        QMessageBox.information(self, "提交成功",
                                "作业已提交，等待教师审核。\n"
                                f"当前预览得分：{pct:.1f}%")

    def _on_error(self, msg):
        self._btn_submit.setEnabled(True)
        self._status.setText("提交失败")
        QMessageBox.critical(self, "提交失败", msg)

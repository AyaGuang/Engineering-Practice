"""前端主窗口 - 通过API调用后端服务"""
import os

from PyQt5.QtWidgets import (QMainWindow, QSplitter, QWidget, QVBoxLayout,
                             QFileDialog, QMessageBox, QStatusBar, QToolBar,
                             QAction, QApplication, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import config
from ui.image_panel import ImagePanel
from ui.answer_panel import AnswerPanel
from ui.result_panel import ResultPanel
from ui.history_panel import HistoryPanel
from api_client import ApiClient


"""
* GradeWorker class
* 批改后台线程，在子线程中通过API调用后端执行OCR识别与批改，避免阻塞UI
* create by XXX
* copyright USTC
* 时间
"""
class GradeWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_client, file_id, questions):
        super().__init__()
        self._api = api_client
        self._file_id = file_id
        self._questions = questions

    def run(self):
        try:
            result = self._api.grade(self._file_id, self._questions)
            if 'error' in result:
                self.error.emit(result['error'])
            else:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


"""
* MainWindow class
* 应用程序主窗口，集成图片预览、答案编辑、批改结果和历史记录等功能面板
* create by XXX
* copyright USTC
* 时间
"""
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._api = ApiClient()
        self._file_id = None
        self._grade_result = None
        self._worker = None
        self._init_ui()
        self._check_backend()

    def _init_ui(self):
        self.setWindowTitle("手写作业OCR识别与批改系统")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 800)

        # 使用TabWidget切换"批改"和"历史"
        self._tabs = QTabWidget()

        # ====== Tab1: 批改页面 ======
        grading_widget = QWidget()
        grading_layout = QVBoxLayout(grading_widget)
        grading_layout.setContentsMargins(0, 0, 0, 0)

        # 创建面板
        self._image_panel = ImagePanel()
        self._answer_panel = AnswerPanel()
        self._result_panel = ResultPanel()

        # 右侧：答案面板 + 结果面板
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self._answer_panel)
        right_splitter.addWidget(self._result_panel)
        right_splitter.setSizes([300, 400])

        # 主分割：图片面板 | 右侧
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self._image_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([500, 600])

        grading_layout.addWidget(main_splitter)

        # ====== Tab2: 历史记录页面 ======
        self._history_panel = HistoryPanel(self._api)

        self._tabs.addTab(grading_widget, "作业批改")
        self._tabs.addTab(self._history_panel, "历史记录")

        self.setCentralWidget(self._tabs)

        self._create_toolbar()
        self._create_menubar()

        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪 - 请加载作业图片并设置标准答案")

    def _create_toolbar(self):
        toolbar = QToolBar("工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_open = QAction("打开图片", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_image)
        toolbar.addAction(act_open)

        toolbar.addSeparator()

        act_grade = QAction("开始批改", self)
        act_grade.setShortcut("Ctrl+G")
        act_grade.triggered.connect(self._start_grading)
        toolbar.addAction(act_grade)

        toolbar.addSeparator()

        act_export_csv = QAction("导出CSV", self)
        act_export_csv.triggered.connect(self._export_csv)
        toolbar.addAction(act_export_csv)

        act_export_html = QAction("导出HTML", self)
        act_export_html.triggered.connect(self._export_html)
        toolbar.addAction(act_export_html)

        toolbar.addSeparator()

        act_history = QAction("历史记录", self)
        act_history.setShortcut("Ctrl+H")
        act_history.triggered.connect(lambda: self._tabs.setCurrentIndex(1))
        toolbar.addAction(act_history)

    def _create_menubar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        act_open = QAction("打开图片", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_image)
        file_menu.addAction(act_open)

        file_menu.addSeparator()

        act_export_csv = QAction("导出CSV报告", self)
        act_export_csv.triggered.connect(self._export_csv)
        file_menu.addAction(act_export_csv)

        act_export_html = QAction("导出HTML报告", self)
        act_export_html.triggered.connect(self._export_html)
        file_menu.addAction(act_export_html)

        file_menu.addSeparator()

        act_quit = QAction("退出", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # 查看菜单
        view_menu = menubar.addMenu("查看")

        act_history = QAction("历史记录", self)
        act_history.setShortcut("Ctrl+H")
        act_history.triggered.connect(lambda: self._tabs.setCurrentIndex(1))
        view_menu.addAction(act_history)

        act_grading = QAction("批改页面", self)
        act_grading.triggered.connect(lambda: self._tabs.setCurrentIndex(0))
        view_menu.addAction(act_grading)

        help_menu = menubar.addMenu("帮助")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _check_backend(self):
        """检查后端服务是否可用"""
        result = self._api.health_check()
        if result.get('status') == 'ok':
            self._statusbar.showMessage("后端服务已连接 - 就绪")
        else:
            self._statusbar.showMessage("警告: 后端服务未启动，请先运行 backend/app.py")

    def _open_image(self):
        self._tabs.setCurrentIndex(0)
        path, _ = QFileDialog.getOpenFileName(self, "选择作业图片", "",
                                              config.IMAGE_FILTER)
        if path:
            self._image_panel.set_image(path)
            self._statusbar.showMessage(f"图片已加载: {os.path.basename(path)}，正在上传...")
            QApplication.processEvents()

            result = self._api.upload_image(path)
            if 'error' in result:
                self._statusbar.showMessage(f"上传失败: {result['error']}")
                QMessageBox.warning(self, "上传失败", result['error'])
            else:
                self._file_id = result['file_id']
                self._statusbar.showMessage(
                    f"图片已上传: {os.path.basename(path)}")

    def _start_grading(self):
        if not self._file_id:
            QMessageBox.warning(self, "提示", "请先加载并上传作业图片")
            return

        questions = self._answer_panel.get_questions()
        if not questions:
            QMessageBox.warning(self, "提示", "请先设置标准答案")
            return

        q_data = [
            {
                "number": q.number,
                "type": q.q_type,
                "answer": q.standard_answer,
                "points": q.points,
            }
            for q in questions
        ]

        self._statusbar.showMessage("正在识别与批改中，请稍候...")
        QApplication.processEvents()

        self._worker = GradeWorker(self._api, self._file_id, q_data)
        self._worker.finished.connect(self._on_grade_done)
        self._worker.error.connect(self._on_grade_error)
        self._worker.start()

    def _on_grade_done(self, result):
        self._grade_result = result

        results = result.get('results', [])
        summary = result.get('summary', {})
        ocr_count = result.get('ocr_count', 0)
        ocr_results = result.get('ocr_results', [])

        self._image_panel.set_ocr_results(ocr_results)
        self._result_panel.display_from_api(results, summary)

        self._statusbar.showMessage(
            f"批改完成(已保存) - 识别{ocr_count}条文本 - "
            f"得分: {summary.get('earned_points', 0)}/{summary.get('total_points', 0)} "
            f"({summary.get('percentage', 0):.1f}%)"
        )

    def _on_grade_error(self, error_msg):
        self._statusbar.showMessage("批改失败")
        QMessageBox.critical(self, "错误", f"批改失败: {error_msg}")

    def _export_csv(self):
        self._do_export('csv')

    def _export_html(self):
        self._do_export('html')

    def _do_export(self, fmt):
        if not self._grade_result:
            QMessageBox.warning(self, "提示", "请先完成批改")
            return

        if fmt == 'csv':
            path, _ = QFileDialog.getSaveFileName(self, "导出CSV", "批改报告.csv",
                                                  config.CSV_FILTER)
        else:
            path, _ = QFileDialog.getSaveFileName(self, "导出HTML", "批改报告.html",
                                                  config.HTML_FILTER)
        if not path:
            return

        result = self._api.export_report(
            self._file_id, self._grade_result['results'], fmt)

        if 'error' in result:
            QMessageBox.warning(self, "导出失败", result['error'])
            return

        with open(path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        self._statusbar.showMessage(f"报告已导出: {path}")

    def _show_about(self):
        QMessageBox.about(self, "关于",
                          "手写作业OCR识别与批改系统\n\n"
                          "架构：前后端分离\n"
                          "前端：PyQt5 桌面客户端\n"
                          "后端：Flask REST API + SQLite\n\n"
                          "功能：\n"
                          "- 手写作业图片OCR识别\n"
                          "- 支持填空题、选择题、计算题批改\n"
                          "- 自动评分与结果导出\n"
                          "- 批改历史记录存储与检索\n\n"
                          "技术栈：PyQt5 + Flask + PaddleOCR + OpenCV + SQLite")

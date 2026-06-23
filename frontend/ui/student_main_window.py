"""
* StudentMainWindow class
* 学生端主窗口 - Tab：提交作业 / 我的成绩
* create by 林文光
* copyright USTC
* 2026.06.22
"""
from PyQt5.QtWidgets import QMainWindow, QTabWidget

from ui.submission_panel import SubmissionPanel
from ui.my_grades_panel import MyGradesPanel


class StudentMainWindow(QMainWindow):
    """学生端主窗口"""

    def __init__(self, api_client, user_id=None, display_name=None,
                 parent=None):
        super().__init__(parent)
        self._api = api_client
        self._user_id = user_id
        self.setWindowTitle("学生端 - 手写作业OCR批改系统")
        self.setMinimumSize(1000, 650)
        self.resize(1150, 750)

        self._tabs = QTabWidget()
        self._submission_panel = SubmissionPanel(self._api)
        self._grades_panel = MyGradesPanel(self._api)
        self._tabs.addTab(self._submission_panel, "提交作业")
        self._tabs.addTab(self._grades_panel, "我的成绩")
        self.setCentralWidget(self._tabs)

        who = display_name or '同学'
        self.statusBar().showMessage(f"学生端 - 欢迎，{who}")

"""
* MyGradesPanel class
* 学生"我的成绩"面板：列出本人提交（后端强制按 X-User-Id 过滤），
* 显示作业名/提交时间/状态/得分；双击查看每题明细
* create by 林文光
* copyright USTC
* 2026.06.23
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QDialog)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer


class MyGradesPanel(QWidget):
    """学生我的成绩面板"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._page = 1
        self._total_pages = 1
        self._submissions = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("我的成绩")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ['作业名', '提交时间', '状态', '得分', '得分率'])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.doubleClicked.connect(self._view_detail)
        layout.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        b_refresh = QPushButton("刷新")
        b_refresh.clicked.connect(self._refresh)
        bottom.addWidget(b_refresh)

        b_detail = QPushButton("查看明细")
        b_detail.clicked.connect(self._view_detail)
        bottom.addWidget(b_detail)

        bottom.addStretch()
        self._page_label = QLabel("第 1 页 / 共 1 页")
        b_prev = QPushButton("上一页")
        b_prev.clicked.connect(self._prev_page)
        b_next = QPushButton("下一页")
        b_next.clicked.connect(self._next_page)
        bottom.addWidget(b_prev)
        bottom.addWidget(self._page_label)
        bottom.addWidget(b_next)
        layout.addLayout(bottom)

        self._note = QLabel('提示：仅"已发布"的作业分数为最终成绩；"待审核"分数为预览，可能被教师调整。')
        self._note.setAlignment(Qt.AlignCenter)
        self._note.setStyleSheet("color:#888; font-size:12px; padding:4px;")
        layout.addWidget(self._note)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh)

    # ---------- 加载 ----------

    def _refresh(self):
        self._page = 1
        self._load()

    def _load(self):
        result = self._api.list_submissions(page=self._page, per_page=15)
        if 'error' in result:
            QMessageBox.warning(self, "加载失败", result['error'])
            return
        self._submissions = result.get('submissions', [])
        total = result.get('total', 0)
        per_page = result.get('per_page', 15)
        self._total_pages = max(1, (total + per_page - 1) // per_page)
        self._display()
        self._page_label.setText(
            f"第 {self._page} 页 / 共 {self._total_pages} 页（共{total}条）")

    def _display(self):
        self._table.setRowCount(0)
        for s in self._submissions:
            row = self._table.rowCount()
            self._table.insertRow(row)

            status = s.get('status', 'pending')
            grading = s.get('grading')
            # list 接口默认不含 grading，分数列在 pending 阶段留空
            if grading:
                earned = grading.get('earned_points', 0)
                total_pts = grading.get('total_points', 0)
                pct = grading.get('percentage', 0)
                score_text = f"{earned} / {total_pts}"
                pct_text = f"{pct:.1f}%"
            else:
                score_text = "—"
                pct_text = "—"

            status_text = '已发布' if status == 'published' else '待审核'
            bg = QColor('#d4edda') if status == 'published' else QColor('#fff3cd')

            items = [
                s.get('assignment_name', ''),
                s.get('submitted_at', ''),
                status_text,
                score_text,
                pct_text,
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(bg)
                self._table.setItem(row, col, item)

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._load()

    def _next_page(self):
        if self._page < self._total_pages:
            self._page += 1
            self._load()

    def _current_submission(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._submissions):
            return None
        return self._submissions[row]

    def _view_detail(self):
        s = self._current_submission()
        if s is None:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        sid = s.get('id')
        detail = self._api.get_submission(sid)
        if 'error' in detail:
            QMessageBox.warning(self, "查看失败", detail['error'])
            return
        SubmissionDetailDialog(detail.get('submission', {}), self).exec_()


"""
* SubmissionDetailDialog class
* 学生提交明细对话框：展示某次提交的状态与每题批改明细
"""
class SubmissionDetailDialog(QDialog):

    def __init__(self, submission, parent=None):
        super().__init__(parent)
        name = submission.get('assignment_name', '')
        status = submission.get('status', 'pending')
        status_text = '已发布' if status == 'published' else '待审核'
        self.setWindowTitle(f"提交明细 - {name}")
        self.setMinimumSize(650, 480)
        self._init_ui(submission, status_text)

    def _init_ui(self, submission, status_text):
        layout = QVBoxLayout(self)

        grading = submission.get('grading') or {}
        info = QLabel(
            f"作业: {submission.get('assignment_name', '')}    "
            f"状态: {status_text}    "
            f"提交时间: {submission.get('submitted_at', '')}    "
            f"得分: {grading.get('earned_points', 0)}/{grading.get('total_points', 0)} "
            f"({grading.get('percentage', 0):.1f}%)")
        info.setStyleSheet("font-size:13px; font-weight:bold; padding:8px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        if status_text == '待审核':
            note = QLabel("该成绩为自动批改预览，教师审核发布前可能调整。")
            note.setStyleSheet("color:#a67c00; padding:2px;")
            layout.addWidget(note)

        results = grading.get('question_results', [])
        table = QTableWidget(len(results), 6)
        table.setHorizontalHeaderLabels(
            ['题号', '题型', '识别文字', '标准答案', '匹配度', '得分'])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        for row, r in enumerate(results):
            bg = QColor('#d4edda') if r.get('is_correct') else QColor('#f8d7da')
            items = [
                str(r.get('number', '')),
                r.get('type_name', ''),
                r.get('recognized_text', '') or '(未识别)',
                r.get('standard_answer', ''),
                f"{r.get('match_score', 0):.0%}",
                f"{r.get('earned_points', 0)}/{r.get('total_points', 0)}",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(bg)
                table.setItem(row, col, item)
        layout.addWidget(table, 1)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

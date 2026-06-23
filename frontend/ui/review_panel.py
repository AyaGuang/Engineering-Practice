"""
* ReviewPanel class
* 教师审核面板：列出提交（默认仅待审核），选中后右侧用可编辑 ResultPanel 改分，
* 支持"保存改分"与"发布"。发布后状态 published，学生即可见。
* create by 林文光
* copyright USTC
* 2026.06.23
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSplitter, QMessageBox,
                             QComboBox, QApplication)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer

from ui.result_panel import ResultPanel


class ReviewPanel(QWidget):
    """教师审核面板"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._submissions = []
        self._current_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("待审核作业")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 左：提交列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        ops = QHBoxLayout()
        ops.addWidget(QLabel("筛选:"))
        self._filter = QComboBox()
        self._filter.addItem("仅待审核", 'pending')
        self._filter.addItem("仅已发布", 'published')
        self._filter.addItem("全部", None)
        self._filter.currentIndexChanged.connect(self._refresh)
        ops.addWidget(self._filter)

        b_refresh = QPushButton("刷新")
        b_refresh.clicked.connect(self._refresh)
        ops.addWidget(b_refresh)
        left_layout.addLayout(ops)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ['ID', '学生', '作业', '提交时间', '状态', '得分率'])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._on_select)
        left_layout.addWidget(self._table, 1)

        # 右：可编辑结果 + 操作
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._result_panel = ResultPanel(editable=True)
        right_layout.addWidget(self._result_panel, 1)

        btns = QHBoxLayout()
        self._lbl_hint = QLabel("请从左侧选择一条提交")
        self._lbl_hint.setStyleSheet("color:#888;")
        btns.addWidget(self._lbl_hint)
        btns.addStretch()

        self._btn_save = QPushButton("保存改分")
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_results)
        btns.addWidget(self._btn_save)

        self._btn_publish = QPushButton("发布")
        self._btn_publish.setEnabled(False)
        self._btn_publish.clicked.connect(self._publish)
        btns.addWidget(self._btn_publish)
        right_layout.addLayout(btns)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([520, 580])
        layout.addWidget(splitter, 1)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh)

    # ---------- 数据 ----------

    def _refresh(self):
        status = self._filter.currentData()
        result = self._api.list_submissions(status=status, per_page=50)
        if 'error' in result:
            QMessageBox.warning(self, "加载失败", result['error'])
            return
        self._submissions = result.get('submissions', [])
        self._display()
        self._reset_detail()

    def _select_by_id(self, sid):
        """刷新后按 id 重新选中并加载详情（id 不在当前列表则忽略）"""
        for i, s in enumerate(self._submissions):
            if s.get('id') == sid:
                self._table.selectRow(i)  # 会触发 _on_select
                return True
        return False

    def _display(self):
        self._table.setRowCount(0)
        for s in self._submissions:
            row = self._table.rowCount()
            self._table.insertRow(row)
            status = s.get('status', 'pending')
            grading = s.get('grading') or {}
            pct = grading.get('percentage', 0)
            status_text = '已发布' if status == 'published' else '待审核'
            bg = QColor('#d4edda') if status == 'published' else QColor('#fff3cd')
            items = [
                str(s.get('id', '')),
                s.get('student_name', '') or '—',
                s.get('assignment_name', '') or '—',
                s.get('submitted_at', ''),
                status_text,
                f"{pct:.1f}%" if grading else '—',
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(bg)
                self._table.setItem(row, col, item)

    def _current_submission(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._submissions):
            return None
        return self._submissions[row]

    def _reset_detail(self):
        self._current_id = None
        self._result_panel.display_from_api([], {'total_points': 0,
                                                  'earned_points': 0,
                                                  'percentage': 0})
        self._btn_save.setEnabled(False)
        self._btn_publish.setEnabled(False)
        self._lbl_hint.setText("请从左侧选择一条提交")

    def _on_select(self):
        s = self._current_submission()
        if not s:
            self._reset_detail()
            return
        sid = s.get('id')
        detail = self._api.get_submission(sid)
        if 'error' in detail:
            QMessageBox.warning(self, "加载失败", detail['error'])
            return
        sub = detail.get('submission', {})
        grading = sub.get('grading') or {}
        results = grading.get('question_results', [])
        summary = {
            'total_points': grading.get('total_points', 0),
            'earned_points': grading.get('earned_points', 0),
            'percentage': grading.get('percentage', 0),
        }
        self._current_id = sid
        self._result_panel.display_from_api(results, summary)
        is_published = sub.get('status') == 'published'
        self._btn_save.setEnabled(bool(results))
        self._btn_publish.setEnabled(not is_published)
        self._lbl_hint.setText(
            f"已选中 #{sid}（{sub.get('student_name', '')} - "
            f"{sub.get('assignment_name', '')}）"
            + ("  [已发布]" if is_published else "  [待审核]"))

    # ---------- 操作 ----------

    def _save_results(self):
        if self._current_id is None:
            return
        sid = self._current_id
        results = self._result_panel.get_adjusted_results()
        if not results:
            QMessageBox.information(self, "提示", "没有可保存的题目")
            return
        QApplication.processEvents()
        resp = self._api.update_submission_results(sid, results)
        if 'error' in resp:
            QMessageBox.warning(self, "保存失败", resp['error'])
            return
        QMessageBox.information(self, "已保存", "改分已保存（尚未发布）")
        self._refresh()
        self._select_by_id(sid)  # 保持选中，方便接着发布

    def _publish(self):
        if self._current_id is None:
            return
        sid = self._current_id
        reply = QMessageBox.question(
            self, "确认发布",
            "发布后该成绩将对学生可见，且状态不可撤回为待审核。\n确定发布？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        resp = self._api.publish_submission(sid)
        if 'error' in resp:
            QMessageBox.warning(self, "发布失败", resp['error'])
            return
        QMessageBox.information(self, "已发布", "成绩已发布，学生现在可查看。")
        self._refresh()

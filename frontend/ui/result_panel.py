"""批改结果展示面板 - 前端版（纯数据驱动，不依赖后端模型）"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


"""
* ResultPanel class
* 批改结果展示面板，以表格形式展示每题的识别文本、匹配度和得分，并汇总总分
* create by XXX
* copyright USTC
* 时间
"""
class ResultPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = None
        self._summary = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("批改结果")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ['题号', '题型', '识别文字', '标准答案', '匹配度', '得分'])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self._table, 1)

        self._summary_label = QLabel("总分: -- / --")
        self._summary_label.setObjectName("summaryLabel")
        self._summary_label.setAlignment(Qt.AlignCenter)
        self._summary_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(self._summary_label)

    def display_from_api(self, results: list, summary: dict):
        """从API返回数据展示批改结果"""
        self._results = results
        self._summary = summary
        self._table.setRowCount(0)

        for r in results:
            row = self._table.rowCount()
            self._table.insertRow(row)

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
                self._table.setItem(row, col, item)

        total = summary.get('total_points', 0)
        earned = summary.get('earned_points', 0)
        pct = summary.get('percentage', 0)
        self._summary_label.setText(
            f"总分: {earned} / {total}  ({pct:.1f}%)"
        )

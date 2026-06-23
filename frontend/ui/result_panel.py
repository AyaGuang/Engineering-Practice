"""批改结果展示面板 - 前端版（纯数据驱动，不依赖后端模型）"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


"""
* ResultPanel class
* 批改结果展示面板，以表格形式展示每题的识别文本、匹配度和得分，并汇总总分。
* editable=True 时（教师审核）"得分"列可双击编辑，改分后自动重算总分，
* 并通过 get_adjusted_results() 暴露改分结果。
* create by 林嘉晨
* copyright USTC
* 2026.02.05
"""
class ResultPanel(QWidget):

    def __init__(self, editable=False, parent=None):
        super().__init__(parent)
        self._results = None
        self._summary = None
        self._editable = editable
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("批改结果" + ("（可编辑得分）" if self._editable else ""))
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ['题号', '题型', '识别文字', '标准答案', '匹配度', '得分'])
        if self._editable:
            self._table.setEditTriggers(
                QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        else:
            self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        # 改分后重算总分
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table, 1)

        self._summary_label = QLabel("总分: -- / --")
        self._summary_label.setObjectName("summaryLabel")
        self._summary_label.setAlignment(Qt.AlignCenter)
        self._summary_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(self._summary_label)

    def _row_number(self, row):
        item = self._table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _row_total(self, row):
        item = self._table.item(row, 5)
        return item.data(Qt.UserRole + 1) if item else 0.0

    def _parse_earned(self, text):
        try:
            return float(str(text).strip())
        except (TypeError, ValueError):
            return None

    def _on_item_changed(self, item):
        """编辑得分单元格后：校验数值并重算总分。"""
        if not self._editable or item.column() != 5:
            return
        earned = self._parse_earned(item.text())
        row = item.row()
        total = self._row_total(row) or 0.0
        if earned is None:
            # 非法输入，恢复为原值（存在 UserRole+2）
            orig = item.data(Qt.UserRole + 2)
            self._table.blockSignals(True)
            item.setText('' if orig is None else str(orig))
            self._table.blockSignals(False)
            return
        earned = max(0.0, min(earned, total)) if total > 0 else max(0.0, earned)
        self._table.blockSignals(True)
        item.setText(f"{earned:g}")
        item.setData(Qt.UserRole + 2, earned)  # 记当前有效值
        self._table.blockSignals(False)
        self._recompute_summary()

    def _recompute_summary(self):
        total_pts = 0.0
        earned_pts = 0.0
        for row in range(self._table.rowCount()):
            total_pts += self._row_total(row)
            it = self._table.item(row, 5)
            earned_pts += self._parse_earned(it.text()) if it else 0.0
        pct = round(earned_pts / total_pts * 100, 2) if total_pts else 0
        self._summary_label.setText(
            f"总分: {earned_pts:g} / {total_pts:g}  ({pct:.1f}%)")

    def display_from_api(self, results: list, summary: dict):
        """从API返回数据展示批改结果"""
        self._results = results
        self._summary = summary
        self._table.blockSignals(True)
        self._table.setRowCount(0)

        for r in results:
            row = self._table.rowCount()
            self._table.insertRow(row)

            earned = r.get('earned_points', 0)
            total_pts = r.get('total_points', 0)
            is_correct = r.get('is_correct', False)
            bg = QColor('#d4edda') if is_correct else QColor('#f8d7da')

            items = [
                str(r.get('number', '')),
                r.get('type_name', ''),
                r.get('recognized_text', '') or '(未识别)',
                r.get('standard_answer', ''),
                f"{r.get('match_score', 0):.0%}",
                f"{earned:g}",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(bg)
                if self._editable:
                    if col == 0:
                        # 题号挂在第0列，供 _row_number 读取
                        item.setData(Qt.UserRole, r.get('number'))
                    elif col == 5:
                        # 总分/当前得分挂在得分列，供 _row_total / 回滚读取
                        item.setData(Qt.UserRole + 1, total_pts)
                        item.setData(Qt.UserRole + 2, earned)
                else:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self._table.setItem(row, col, item)

        self._table.blockSignals(False)

        total = summary.get('total_points', 0)
        earned_s = summary.get('earned_points', 0)
        pct = summary.get('percentage', 0)
        self._summary_label.setText(
            f"总分: {earned_s} / {total}  ({pct:.1f}%)"
        )

    def get_adjusted_results(self) -> list:
        """返回所有题的当前改分结果 [{number, earned_points, is_correct}]。
        供教师审核保存改分调用。"""
        out = []
        for row in range(self._table.rowCount()):
            number = self._row_number(row)
            if number is None:
                continue
            it = self._table.item(row, 5)
            earned = self._parse_earned(it.text()) if it else 0.0
            total = self._row_total(row)
            out.append({
                'number': number,
                'earned_points': earned or 0.0,
                'is_correct': bool(total and earned >= total),
            })
        return out

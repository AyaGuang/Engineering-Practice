"""历史记录面板 - 查询和浏览批改历史"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QDateEdit, QSpinBox,
                             QMessageBox, QDialog, QTextBrowser, QDoubleSpinBox,
                             QGroupBox, QFormLayout)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDate, pyqtSignal


"""
* HistoryPanel class
* 历史记录面板，支持按文件名、日期、分数范围检索批改历史，提供分页浏览和删除功能
* create by XXX
* copyright USTC
* 时间
"""
class HistoryPanel(QWidget):
    detail_requested = pyqtSignal(dict)  # 点击查看详情时发射

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._current_page = 1
        self._total_pages = 1
        self._records = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("批改历史记录")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 搜索条件区
        search_group = QGroupBox("搜索条件")
        search_layout = QFormLayout()

        # 关键词
        self._keyword_input = QLineEdit()
        self._keyword_input.setPlaceholderText("按文件名搜索...")
        search_layout.addRow("文件名:", self._keyword_input)

        # 日期范围
        date_layout = QHBoxLayout()
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(self._date_from)
        date_layout.addWidget(QLabel("至"))
        date_layout.addWidget(self._date_to)
        search_layout.addRow("日期范围:", date_layout)

        # 得分率范围
        score_layout = QHBoxLayout()
        self._min_score = QDoubleSpinBox()
        self._min_score.setRange(0, 100)
        self._min_score.setValue(0)
        self._min_score.setSuffix("%")
        self._max_score = QDoubleSpinBox()
        self._max_score.setRange(0, 100)
        self._max_score.setValue(100)
        self._max_score.setSuffix("%")
        score_layout.addWidget(self._min_score)
        score_layout.addWidget(QLabel("至"))
        score_layout.addWidget(self._max_score)
        search_layout.addRow("得分率:", score_layout)

        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # 搜索按钮
        btn_layout = QHBoxLayout()
        btn_search = QPushButton("搜索")
        btn_search.clicked.connect(self._do_search)
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self._refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_search)
        btn_layout.addWidget(btn_refresh)
        layout.addLayout(btn_layout)

        # 结果表格
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ['ID', '文件名', '批改时间', '总分', '得分', '得分率'])
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self._table, 1)

        # 底部：分页 + 操作按钮
        bottom_layout = QHBoxLayout()

        btn_detail = QPushButton("查看详情")
        btn_detail.clicked.connect(self._view_detail)
        btn_delete = QPushButton("删除记录")
        btn_delete.clicked.connect(self._delete_record)
        bottom_layout.addWidget(btn_detail)
        bottom_layout.addWidget(btn_delete)

        bottom_layout.addStretch()

        # 分页控件
        self._page_label = QLabel("第 1 页 / 共 1 页")
        btn_prev = QPushButton("上一页")
        btn_prev.clicked.connect(self._prev_page)
        btn_next = QPushButton("下一页")
        btn_next.clicked.connect(self._next_page)
        bottom_layout.addWidget(btn_prev)
        bottom_layout.addWidget(self._page_label)
        bottom_layout.addWidget(btn_next)

        layout.addLayout(bottom_layout)

        # 统计信息
        self._stats_label = QLabel("")
        self._stats_label.setAlignment(Qt.AlignCenter)
        self._stats_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(self._stats_label)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _do_search(self):
        self._current_page = 1
        self._load_data()

    def _refresh(self):
        self._current_page = 1
        self._keyword_input.clear()
        self._load_data()
        self._load_statistics()

    def _load_data(self):
        """从后端加载历史数据"""
        params = {
            'page': self._current_page,
            'per_page': 15,
        }

        keyword = self._keyword_input.text().strip()
        if keyword:
            params['keyword'] = keyword

        params['date_from'] = self._date_from.date().toString('yyyy-MM-dd')
        params['date_to'] = self._date_to.date().toString('yyyy-MM-dd')

        min_s = self._min_score.value()
        max_s = self._max_score.value()
        if min_s > 0:
            params['min_score'] = min_s
        if max_s < 100:
            params['max_score'] = max_s

        result = self._api.get_history(**params)
        if 'error' in result:
            return

        self._records = result.get('records', [])
        total = result.get('total', 0)
        per_page = result.get('per_page', 15)
        self._total_pages = max(1, (total + per_page - 1) // per_page)

        self._display_records()
        self._page_label.setText(
            f"第 {self._current_page} 页 / 共 {self._total_pages} 页 (共{total}条)")

    def _display_records(self):
        self._table.setRowCount(0)
        for rec in self._records:
            row = self._table.rowCount()
            self._table.insertRow(row)

            pct = rec.get('percentage', 0)
            if pct >= 80:
                bg = QColor('#d4edda')
            elif pct >= 60:
                bg = QColor('#fff3cd')
            else:
                bg = QColor('#f8d7da')

            items = [
                str(rec.get('id', '')),
                rec.get('original_filename', ''),
                rec.get('grade_time', ''),
                str(rec.get('total_points', 0)),
                str(rec.get('earned_points', 0)),
                f"{pct:.1f}%",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(bg)
                self._table.setItem(row, col, item)

    def _load_statistics(self):
        stats = self._api.get_statistics()
        if 'error' not in stats:
            self._stats_label.setText(
                f"统计: 共{stats.get('total_homeworks', 0)}份作业, "
                f"{stats.get('total_gradings', 0)}次批改, "
                f"平均得分率 {stats.get('avg_percentage', 0):.1f}%")

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_data()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_data()

    def _get_selected_record(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._records):
            return None
        return self._records[row]

    def _on_row_double_clicked(self, index):
        self._view_detail()

    def _view_detail(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return

        grading_id = rec.get('id')
        detail = self._api.get_history_detail(grading_id)
        if 'error' in detail:
            QMessageBox.warning(self, "错误", detail['error'])
            return

        # 弹出详情对话框
        dlg = DetailDialog(detail, self)
        dlg.exec_()

    def _delete_record(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除批改记录 #{rec.get('id')} ({rec.get('original_filename', '')}) 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            result = self._api.delete_history(rec.get('id'))
            if 'error' not in result:
                self._load_data()
                self._load_statistics()
            else:
                QMessageBox.warning(self, "删除失败", result.get('error', ''))


"""
* DetailDialog class
* 批改详情对话框，弹窗展示单次批改的完整信息，包括每题识别结果和得分明细
* create by XXX
* copyright USTC
* 时间
"""
class DetailDialog(QDialog):

    def __init__(self, detail, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"批改详情 - {detail.get('original_filename', '')}")
        self.setMinimumSize(650, 500)
        self._init_ui(detail)

    def _init_ui(self, detail):
        layout = QVBoxLayout(self)

        # 基本信息
        info = QLabel(
            f"文件: {detail.get('original_filename', '')}    "
            f"时间: {detail.get('grade_time', '')}    "
            f"得分: {detail.get('earned_points', 0)}/{detail.get('total_points', 0)} "
            f"({detail.get('percentage', 0):.1f}%)")
        info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(info)

        # 每题结果表格
        results = detail.get('question_results', [])
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

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

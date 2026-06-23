"""
* AssignmentPanel class
* 教师作业管理面板 - 列出/新建/编辑/关闭/删除作业（持久化的标准答案集合）
* 右侧编辑器复用 AnswerPanel 进行题目编辑
* create by 林文光
* copyright USTC
* 2026.06.22
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QSplitter, QLineEdit, QMessageBox, QHeaderView,
                             QAbstractItemView)
from PyQt5.QtCore import Qt

from ui.answer_panel import AnswerPanel


class AssignmentPanel(QWidget):
    """教师作业管理面板"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._editing_id = None  # 当前编辑的作业 id，None=新建
        self._init_ui()
        self.refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # ===== 左：作业列表 =====
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_title = QLabel("作业列表")
        left_title.setObjectName("panelTitle")
        left_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_title)

        self._list = QTableWidget(0, 4)
        self._list.setHorizontalHeaderLabels(['ID', '作业名', '状态', '题数'])
        self._list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        hdr = self._list.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._list.itemSelectionChanged.connect(self._on_select)
        left_layout.addWidget(self._list, 1)

        list_btns = QHBoxLayout()
        b_new = QPushButton("新建作业")
        b_refresh = QPushButton("刷新")
        b_toggle = QPushButton("切换开放状态")
        b_del = QPushButton("删除选中")
        b_new.clicked.connect(self._on_new)
        b_refresh.clicked.connect(self.refresh_list)
        b_toggle.clicked.connect(self._on_toggle_status)
        b_del.clicked.connect(self._on_delete)
        for b in [b_new, b_refresh, b_toggle, b_del]:
            list_btns.addWidget(b)
        left_layout.addLayout(list_btns)

        # ===== 右：编辑器 =====
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_title = QLabel("作业编辑")
        right_title.setObjectName("panelTitle")
        right_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_title)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("作业名:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如：第一章练习")
        name_row.addWidget(self._name_edit, 1)
        right_layout.addLayout(name_row)

        # 复用 AnswerPanel 编辑题目（不传 api_client，避免重复显示"存为作业"按钮）
        self._editor = AnswerPanel(api_client=None)
        right_layout.addWidget(self._editor, 1)

        save_row = QHBoxLayout()
        save_row.addStretch()
        b_save = QPushButton("保存作业")
        b_save.clicked.connect(self._on_save)
        save_row.addWidget(b_save)
        right_layout.addLayout(save_row)

        # ===== 主分割 =====
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter, 1)

    # ---------- 列表 ----------

    def refresh_list(self):
        result = self._api.list_assignments()
        if 'error' in result:
            QMessageBox.warning(self, "加载失败", result['error'])
            return
        self._list.setRowCount(0)
        for a in result.get('assignments', []):
            row = self._list.rowCount()
            self._list.insertRow(row)
            self._fill_cell(row, 0, str(a.get('id', '')))
            self._fill_cell(row, 1, a.get('name', ''))
            status = a.get('status', 'active')
            self._fill_cell(row, 2, '开放' if status == 'active' else '已关闭')
            self._fill_cell(row, 3, str(a.get('question_count', 0)))
            # 缓存 id 到第0列的 data
            id_item = self._list.item(row, 0)
            if id_item:
                id_item.setData(Qt.UserRole, a.get('id'))
                id_item.setData(Qt.UserRole + 1, status)

    def _fill_cell(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self._list.setItem(row, col, item)

    def _current_assignment_id(self):
        row = self._list.currentRow()
        if row < 0:
            return None
        item = self._list.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _current_status(self):
        row = self._list.currentRow()
        if row < 0:
            return None
        item = self._list.item(row, 0)
        return item.data(Qt.UserRole + 1) if item else None

    # ---------- 选择/编辑 ----------

    def _on_select(self):
        aid = self._current_assignment_id()
        if aid is None:
            return
        result = self._api.get_assignment(aid)
        if 'error' in result:
            QMessageBox.warning(self, "加载失败", result['error'])
            return
        a = result.get('assignment', {})
        self._editing_id = a.get('id')
        self._name_edit.setText(a.get('name', ''))
        self._editor.set_questions(a.get('questions', []))

    def _on_new(self):
        self._editing_id = None
        self._name_edit.clear()
        self._editor.set_questions([])
        self._name_edit.setFocus()

    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入作业名")
            return
        questions = self._editor.get_questions_dicts()
        if not questions:
            QMessageBox.warning(self, "提示", "请至少添加一道题")
            return
        if self._editing_id is None:
            result = self._api.create_assignment(name, questions)
        else:
            result = self._api.update_assignment(
                self._editing_id, name=name, questions=questions)
        if 'error' in result:
            QMessageBox.warning(self, "保存失败", result['error'])
            return
        QMessageBox.information(self, "成功", "作业已保存")
        self.refresh_list()

    def _on_toggle_status(self):
        aid = self._current_assignment_id()
        if aid is None:
            QMessageBox.information(self, "提示", "请先选中一个作业")
            return
        cur = self._current_status()
        new_status = 'closed' if cur == 'active' else 'active'
        result = self._api.update_assignment(aid, status=new_status)
        if 'error' in result:
            QMessageBox.warning(self, "失败", result['error'])
            return
        self.refresh_list()

    def _on_delete(self):
        aid = self._current_assignment_id()
        if aid is None:
            QMessageBox.information(self, "提示", "请先选中一个作业")
            return
        reply = QMessageBox.question(
            self, "确认删除", "确定删除该作业及其所有提交吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        result = self._api.delete_assignment(aid)
        if 'error' in result:
            QMessageBox.warning(self, "删除失败", result['error'])
            return
        self._on_new()
        self.refresh_list()

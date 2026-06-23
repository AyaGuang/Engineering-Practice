"""
* UserManagePanel class
* 教师账号管理面板：增删学生账号。复用 /api/users 接口。
* create by 林文光
* copyright USTC
* 2026.06.23
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QComboBox, QMessageBox,
                             QGroupBox, QFormLayout, QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer


class UserManagePanel(QWidget):
    """教师账号管理面板"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("账号管理")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 新建账号区
        group = QGroupBox("新建账号")
        form = QFormLayout()
        self._inp_user = QLineEdit()
        self._inp_user.setPlaceholderText("登录账号（如 stu01）")
        form.addRow("账号:", self._inp_user)

        self._inp_pwd = QLineEdit()
        self._inp_pwd.setPlaceholderText("密码")
        form.addRow("密码:", self._inp_pwd)

        self._inp_name = QLineEdit()
        self._inp_name.setPlaceholderText("可选，默认同账号")
        form.addRow("姓名:", self._inp_name)

        self._combo_role = QComboBox()
        self._combo_role.addItem("学生", 'student')
        self._combo_role.addItem("教师", 'teacher')
        form.addRow("角色:", self._combo_role)

        btn_row = QHBoxLayout()
        b_add = QPushButton("新建")
        b_add.clicked.connect(self._on_add)
        b_clear = QPushButton("清空")
        b_clear.clicked.connect(self._clear_form)
        btn_row.addWidget(b_add)
        btn_row.addWidget(b_clear)
        btn_row.addStretch()
        form.addRow(btn_row)
        group.setLayout(form)
        layout.addWidget(group)

        # 账号列表
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选角色:"))
        self._filter_role = QComboBox()
        self._filter_role.addItem("仅学生", 'student')
        self._filter_role.addItem("仅教师", 'teacher')
        self._filter_role.addItem("全部", None)
        self._filter_role.currentIndexChanged.connect(self._refresh)
        filter_row.addWidget(self._filter_role)
        filter_row.addStretch()
        b_refresh = QPushButton("刷新")
        b_refresh.clicked.connect(self._refresh)
        filter_row.addWidget(b_refresh)
        layout.addLayout(filter_row)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ['ID', '账号', '姓名', '角色', '创建时间'])
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        b_del = QPushButton("删除选中")
        b_del.clicked.connect(self._on_delete)
        bottom.addWidget(b_del)
        bottom.addStretch()
        layout.addLayout(bottom)

    # ---------- 操作 ----------

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh)

    def _refresh(self):
        role = self._filter_role.currentData()  # None = 全部
        result = self._api.list_users(role=role)
        if 'error' in result:
            QMessageBox.warning(self, "加载失败", result['error'])
            return
        users = result.get('users', [])

        self._table.setRowCount(0)
        for u in users:
            row = self._table.rowCount()
            self._table.insertRow(row)
            items = [
                str(u.get('id', '')),
                u.get('username', ''),
                u.get('display_name', ''),
                '教师' if u.get('role') == 'teacher' else '学生',
                u.get('created_at', ''),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, u.get('id'))
                self._table.setItem(row, col, item)

    def _clear_form(self):
        self._inp_user.clear()
        self._inp_pwd.clear()
        self._inp_name.clear()

    def _on_add(self):
        username = self._inp_user.text().strip()
        password = self._inp_pwd.text()
        name = self._inp_name.text().strip()
        role = self._combo_role.currentData()
        if not username or not password:
            QMessageBox.information(self, "提示", "请输入账号和密码")
            return
        result = self._api.create_user(username, password, role=role,
                                       display_name=name)
        if 'error' in result:
            QMessageBox.warning(self, "创建失败", result['error'])
            return
        QMessageBox.information(self, "成功", "账号已创建")
        self._clear_form()
        self._refresh()

    def _on_delete(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中一个账号")
            return
        uid = self._table.item(row, 0).data(Qt.UserRole)
        uname = self._table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除账号 {uname} 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        result = self._api.delete_user(uid)
        if 'error' in result:
            QMessageBox.warning(self, "删除失败", result['error'])
            return
        self._refresh()

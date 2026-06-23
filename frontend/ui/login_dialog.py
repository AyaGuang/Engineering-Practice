"""
* LoginDialog class
* 登录对话框 - 账号密码登录，登录成功后暴露 user_id/role/display_name 供路由
* create by 林文光
* copyright USTC
* 2026.06.22
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QPushButton, QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt


class LoginDialog(QDialog):
    """账号密码登录对话框"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self.user_id = None
        self.role = None
        self.username = None
        self.display_name = None
        self.setWindowTitle("登录 - 手写作业OCR批改系统")
        self.setMinimumWidth(380)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("手写作业OCR识别与批改系统")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("首次使用请用 teacher / teacher 登录")
        hint.setStyleSheet("color:#666; font-size:12px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        form = QFormLayout()
        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("请输入账号")
        self._pwd_edit = QLineEdit()
        self._pwd_edit.setPlaceholderText("请输入密码")
        self._pwd_edit.setEchoMode(QLineEdit.Password)
        form.addRow("账号:", self._user_edit)
        form.addRow("密码:", self._pwd_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._login_btn = QPushButton("登录")
        self._login_btn.setDefault(True)
        self._login_btn.clicked.connect(self._on_login)
        btn_row.addWidget(self._login_btn)
        layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet("color:#d9534f; font-size:12px;")
        self._status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status)

        self._user_edit.returnPressed.connect(self._on_login)
        self._pwd_edit.returnPressed.connect(self._on_login)
        self._user_edit.setFocus()

    def _on_login(self):
        username = self._user_edit.text().strip()
        password = self._pwd_edit.text()
        if not username or not password:
            self._status.setText("请输入账号和密码")
            return
        self._login_btn.setEnabled(False)
        self._status.setStyleSheet("color:#666; font-size:12px;")
        self._status.setText("登录中...")
        self.repaint()

        result = self._api.login(username, password)
        self._login_btn.setEnabled(True)
        self._status.setStyleSheet("color:#d9534f; font-size:12px;")

        if result.get('ok'):
            self.user_id = result.get('user_id')
            self.role = result.get('role')
            self.username = result.get('username')
            self.display_name = result.get('display_name')
            self.accept()
        else:
            self._status.setText(result.get('error', '登录失败'))

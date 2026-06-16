"""
* SettingsDialog class
* LLM设置对话框 - 配置API Key、Base URL、模型名等
* create by 林文光
* copyright USTC
* 2026.06.13
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QSpinBox, QPushButton, QHBoxLayout, QLabel,
                             QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class _TestWorker(QThread):
    """后台测试连接，避免阻塞UI"""
    finished_signal = pyqtSignal(dict)

    def __init__(self, api_client, settings):
        super().__init__()
        self._api = api_client
        self._settings = settings

    def run(self):
        result = self._api.test_settings(self._settings)
        self.finished_signal.emit(result)


class SettingsDialog(QDialog):
    """LLM配置对话框"""

    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._test_worker = None
        self.setWindowTitle("AI 纠错设置")
        self.setMinimumWidth(420)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        hint = QLabel("配置 LLM API 以启用 AI 纠错功能。\n"
                      "设置会保存到用户目录 ~/.homework_grader/settings.json")
        hint.setStyleSheet("color: #666; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        form.addRow("API Key:", self._api_key_edit)

        self._base_url_edit = QLineEdit()
        self._base_url_edit.setPlaceholderText("留空使用默认；DeepSeek 填 https://api.deepseek.com")
        form.addRow("Base URL:", self._base_url_edit)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("如 deepseek-v4-flash")
        form.addRow("模型名:", self._model_edit)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 300)
        self._timeout_spin.setSuffix(" 秒")
        form.addRow("超时:", self._timeout_spin)

        layout.addLayout(form)

        # 按钮区
        btn_layout = QHBoxLayout()

        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._on_test)
        btn_layout.addWidget(self._test_btn)

        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self._status_label)

    def _load_settings(self):
        """从后端加载当前配置"""
        result = self._api.get_settings()
        if 'error' in result:
            self._status_label.setText(f"加载失败: {result['error']}")
            return
        # api_key脱敏返回，若已设置则显示占位
        if result.get('api_key_set'):
            self._api_key_edit.setPlaceholderText("（已设置，留空则不修改）")
        self._base_url_edit.setText(result.get('base_url', ''))
        self._model_edit.setText(result.get('model', ''))
        self._timeout_spin.setValue(int(result.get('timeout', 30)))

    def _collect_settings(self):
        """收集表单数据。api_key为空时不覆盖（保留原值）。"""
        api_key = self._api_key_edit.text().strip()
        if not api_key:
            api_key = None  # 不修改
        return {
            'api_key': api_key,
            'base_url': self._base_url_edit.text().strip(),
            'model': self._model_edit.text().strip(),
            'timeout': self._timeout_spin.value(),
        }

    def _on_test(self):
        """测试连接"""
        settings = self._collect_settings()
        api_key = settings['api_key']
        if not api_key:
            self._status_label.setText("请先填写API Key")
            self._status_label.setStyleSheet("color: #d9534f; font-size: 12px;")
            return

        self._test_btn.setEnabled(False)
        self._status_label.setText("测试中...")
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        QApplication_ref = __import__('PyQt5.QtWidgets', fromlist=['QApplication'])
        QApplication_ref.QApplication.processEvents()

        self._test_worker = _TestWorker(self._api, settings)
        self._test_worker.finished_signal.connect(self._on_test_done)
        self._test_worker.start()

    def _on_test_done(self, result):
        self._test_btn.setEnabled(True)
        if result.get('ok'):
            reply = result.get('reply', '')
            self._status_label.setText(f"✓ 连接成功！模型回复: {reply}")
            self._status_label.setStyleSheet("color: #5cb85c; font-size: 12px;")
        else:
            err = result.get('error', '未知错误')
            self._status_label.setText(f"✗ 连接失败: {err}")
            self._status_label.setStyleSheet("color: #d9534f; font-size: 12px;")

    def _on_save(self):
        """保存设置"""
        settings = self._collect_settings()
        result = self._api.update_settings(settings)
        if 'error' in result:
            QMessageBox.warning(self, "保存失败", result['error'])
            return
        QMessageBox.information(self, "成功", "设置已保存")
        self.accept()

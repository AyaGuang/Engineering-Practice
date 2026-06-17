"""
* SettingsDialog class
* LLM设置对话框 - 配置API Key、Base URL、模型名等
* create by 林文光
* copyright USTC
* 2026.06.13
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QSpinBox, QPushButton, QHBoxLayout, QLabel,
                             QMessageBox, QApplication, QCheckBox,
                             QComboBox, QGroupBox)
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
        self.setWindowTitle("批改设置")
        self.setMinimumWidth(420)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        hint = QLabel("配置 LLM API 与批改行为选项。\n"
                      "设置会保存到用户目录 ~/.homework_grader/settings.json")
        hint.setStyleSheet("color: #666; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ===== LLM 配置分组 =====
        llm_group = QGroupBox("LLM 纠错配置")
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

        llm_group.setLayout(form)
        layout.addWidget(llm_group)

        # ===== 批改选项分组 =====
        grade_group = QGroupBox("批改选项")
        grade_layout = QVBoxLayout()

        self._llm_checkbox = QCheckBox("启用 AI 纠错（需配置上方 API Key）")
        self._llm_checkbox.setToolTip("调用 LLM 纠正 OCR 识别错误，并按语义匹配答案\n需先填写 API Key")
        grade_layout.addWidget(self._llm_checkbox)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("答案匹配模式:"))
        self._match_mode_combo = QComboBox()
        self._match_mode_combo.addItem("题号匹配", 'by_number')
        self._match_mode_combo.addItem("位置匹配", 'by_position')
        self._match_mode_combo.setToolTip(
            "题号匹配：按题号对应（适合无撞号作业）\n"
            "位置匹配：识别答案与标准答案从上到下一一对应\n"
            "         （适合嵌套题号/①②③结构）")
        mode_row.addWidget(self._match_mode_combo)
        mode_row.addStretch()
        grade_layout.addLayout(mode_row)

        self._enhance_checkbox = QCheckBox("选择题增强（跳过选项行，适用于答案写在题干括号的试卷）")
        self._enhance_checkbox.setToolTip(
            "开启后解析时跳过 A./B./C./D. 选项行，\n"
            "避免选项字母污染答案提取。\n"
            "适用于答案写在题干括号里的试卷格式。")
        grade_layout.addWidget(self._enhance_checkbox)

        grade_group.setLayout(grade_layout)
        layout.addWidget(grade_group)

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
        # 批改选项
        self._llm_checkbox.setChecked(bool(result.get('enable_llm_correction', False)))
        match_mode = result.get('match_mode', 'by_number')
        idx = self._match_mode_combo.findData(match_mode)
        if idx >= 0:
            self._match_mode_combo.setCurrentIndex(idx)
        self._enhance_checkbox.setChecked(bool(result.get('enhance_choice', False)))

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
            'enable_llm_correction': self._llm_checkbox.isChecked(),
            'match_mode': self._match_mode_combo.currentData(),
            'enhance_choice': self._enhance_checkbox.isChecked(),
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
        QApplication.processEvents()

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

"""标准答案输入面板 - 前端版（不依赖后端模型）"""
import json
from dataclasses import dataclass
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QHeaderView, QFileDialog, QMessageBox,
                             QCheckBox)
from PyQt5.QtCore import Qt

import config

# 题型映射（前端本地定义，与后端QuestionType.value对应）
TYPE_NAMES = ['填空题', '选择题', '计算题']
TYPE_VALUE_MAP = {
    '填空题': 'fill_blank',
    '选择题': 'multiple_choice',
    '计算题': 'calculation',
}
VALUE_TYPE_MAP = {v: k for k, v in TYPE_VALUE_MAP.items()}


"""
* QuestionData class
* 前端用的轻量级题目数据类，存储题号、题型、标准答案和分值
* create by 林嘉晨
* copyright USTC
* 2026.02.02
"""
@dataclass
class QuestionData:
    number: int
    q_type: str         # 'fill_blank', 'multiple_choice', 'calculation'
    standard_answer: str
    points: float = 1.0

    @property
    def type_display(self):
        return VALUE_TYPE_MAP.get(self.q_type, '填空题')


"""
* AnswerPanel class
* 标准答案编辑面板，提供答案模板的增删改查、保存和加载功能
* create by 林嘉晨
* copyright USTC
* 2026.02.02
"""
class AnswerPanel(QWidget):

    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self._api = api_client
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("标准答案模板")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(['题号', '题型', '标准答案', '分值'])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self._table, 1)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加")
        btn_del = QPushButton("删除")
        btn_load = QPushButton("加载模板")
        btn_save = QPushButton("保存模板")

        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._del_row)
        btn_load.clicked.connect(self._load_template)
        btn_save.clicked.connect(self._save_template)

        for btn in [btn_add, btn_del, btn_load, btn_save]:
            btn_layout.addWidget(btn)

        # 接入 api_client（教师端）时提供"存为作业"按钮，把当前答案持久化为作业
        if self._api is not None:
            btn_save_hw = QPushButton("存为作业")
            btn_save_hw.setToolTip("把当前标准答案保存为一份作业（供学生提交）")
            btn_save_hw.clicked.connect(self._save_as_assignment)
            btn_layout.addWidget(btn_save_hw)

        btn_layout.addStretch()

        self._llm_checkbox = QCheckBox("启用 AI 纠错")
        self._llm_checkbox.setToolTip('使用 LLM 纠正 OCR 识别中的明显错误\n'
                                      '默认值可在【设置】中配置，此处可临时切换')
        btn_layout.addWidget(self._llm_checkbox)

        layout.addLayout(btn_layout)

        for _ in range(3):
            self._add_row()

    def _add_row(self):
        row = self._table.rowCount()
        self._table.insertRow(row)

        num_item = QTableWidgetItem(str(row + 1))
        num_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 0, num_item)

        combo = QComboBox()
        combo.addItems(TYPE_NAMES)
        self._table.setCellWidget(row, 1, combo)

        self._table.setItem(row, 2, QTableWidgetItem(''))

        pts_item = QTableWidgetItem('2')
        pts_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 3, pts_item)

    def _del_row(self):
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def get_questions(self) -> list:
        """获取所有标准答案，返回QuestionData列表"""
        questions = []
        for row in range(self._table.rowCount()):
            try:
                num = int(self._table.item(row, 0).text())
            except (ValueError, AttributeError):
                num = row + 1

            combo = self._table.cellWidget(row, 1)
            q_type = TYPE_VALUE_MAP.get(combo.currentText(), 'fill_blank')

            answer_item = self._table.item(row, 2)
            answer = answer_item.text() if answer_item else ''

            try:
                points = float(self._table.item(row, 3).text())
            except (ValueError, AttributeError):
                points = 1.0

            questions.append(QuestionData(
                number=num, q_type=q_type,
                standard_answer=answer, points=points
            ))
        return questions

    def is_llm_correction_enabled(self) -> bool:
        """是否启用了LLM纠错（本次批改的快捷开关）"""
        return self._llm_checkbox.isChecked()

    def set_llm_correction_enabled(self, enabled: bool) -> None:
        """设置LLM纠错复选框状态（用于同步设置默认值）"""
        self._llm_checkbox.setChecked(bool(enabled))

    def _add_row_from_dict(self, q_data: dict):
        """根据字典在表格末尾插入一行：{number,type,answer,points}"""
        row = self._table.rowCount()
        self._table.insertRow(row)

        num_item = QTableWidgetItem(str(q_data.get('number', row + 1)))
        num_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 0, num_item)

        combo = QComboBox()
        combo.addItems(TYPE_NAMES)
        q_type_str = q_data.get('type', 'fill_blank')
        combo.setCurrentText(VALUE_TYPE_MAP.get(q_type_str, '填空题'))
        self._table.setCellWidget(row, 1, combo)

        self._table.setItem(row, 2, QTableWidgetItem(q_data.get('answer', '')))

        pts_item = QTableWidgetItem(str(q_data.get('points', 1.0)))
        pts_item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 3, pts_item)

    def set_questions(self, questions: list):
        """从字典列表填充表格：[{number,type,answer,points}, ...]"""
        self._table.setRowCount(0)
        for q_data in questions:
            self._add_row_from_dict(q_data)

    def get_questions_dicts(self) -> list:
        """返回标准答案的 dict 列表（用于作业 API）"""
        return [
            {"number": q.number, "type": q.q_type,
             "answer": q.standard_answer, "points": q.points}
            for q in self.get_questions()
        ]

    def _save_as_assignment(self):
        """把当前答案保存为作业（教师端）"""
        if self._api is None:
            return
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "存为作业", "请输入作业名称：")
        if not ok or not name.strip():
            return
        questions = self.get_questions_dicts()
        if not questions:
            QMessageBox.warning(self, "提示", "请先设置标准答案")
            return
        result = self._api.create_assignment(name.strip(), questions)
        if 'error' in result:
            QMessageBox.warning(self, "失败", result['error'])
        else:
            QMessageBox.information(self, "成功", f"已存为作业：{name.strip()}")

    def _save_template(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存答案模板", "",
                                              config.TEMPLATE_FILTER)
        if not path:
            return
        questions = self.get_questions()
        data = {
            "questions": [
                {
                    "number": q.number,
                    "type": q.q_type,
                    "answer": q.standard_answer,
                    "points": q.points,
                }
                for q in questions
            ]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "成功", "模板已保存")

    def _load_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载答案模板", "",
                                              config.TEMPLATE_FILTER)
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载失败: {e}")
            return

        self._table.setRowCount(0)
        for q_data in data.get('questions', []):
            self._add_row_from_dict(q_data)

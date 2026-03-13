"""标准答案输入面板 - 前端版（不依赖后端模型）"""
import json
from dataclasses import dataclass
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QHeaderView, QFileDialog, QMessageBox)
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
* create by XXX
* copyright USTC
* 时间
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
* create by XXX
* copyright USTC
* 时间
"""
class AnswerPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
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
            row = self._table.rowCount()
            self._table.insertRow(row)

            num_item = QTableWidgetItem(str(q_data.get('number', row + 1)))
            num_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, num_item)

            combo = QComboBox()
            combo.addItems(TYPE_NAMES)
            q_type_str = q_data.get('type', 'fill_blank')
            display_name = VALUE_TYPE_MAP.get(q_type_str, '填空题')
            combo.setCurrentText(display_name)
            self._table.setCellWidget(row, 1, combo)

            self._table.setItem(row, 2, QTableWidgetItem(q_data.get('answer', '')))

            pts_item = QTableWidgetItem(str(q_data.get('points', 1.0)))
            pts_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, pts_item)

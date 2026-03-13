"""图片预览面板"""
import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QButtonGroup, QRadioButton, QScrollArea)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal


"""
* ImagePanel class
* 图片预览面板，支持加载显示作业图片、原图与处理图切换、OCR识别文字展示
* create by XXX
* copyright USTC
* 时间
"""
class ImagePanel(QWidget):
    image_loaded = pyqtSignal(str)  # 发射图片路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_img = None      # 原始图片 (numpy)
        self._processed_img = None     # 处理后图片 (numpy)
        self._show_processed = False
        self._show_ocr = False         # 是否显示OCR文字
        self._ocr_results = None       # OCR识别结果
        self._image_path = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 标题
        title = QLabel("图片预览")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 图片显示区域（可滚动）
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMinimumSize(400, 300)
        self._image_label = QLabel("请加载作业图片")
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("color: #888; font-size: 16px;")
        self._scroll.setWidget(self._image_label)
        layout.addWidget(self._scroll, 1)

        # 底部按钮栏
        switch_layout = QHBoxLayout()
        self._btn_group = QButtonGroup(self)
        self._rb_original = QRadioButton("原图")
        self._rb_processed = QRadioButton("处理后")
        self._rb_original.setChecked(True)
        self._btn_group.addButton(self._rb_original, 0)
        self._btn_group.addButton(self._rb_processed, 1)
        self._btn_group.buttonClicked[int].connect(self._on_switch)

        # OCR文字切换按钮
        self._btn_ocr = QPushButton("显示识别文字")
        self._btn_ocr.setCheckable(True)
        self._btn_ocr.setEnabled(False)
        self._btn_ocr.clicked.connect(self._on_toggle_ocr)

        switch_layout.addStretch()
        switch_layout.addWidget(self._rb_original)
        switch_layout.addWidget(self._rb_processed)
        switch_layout.addWidget(self._btn_ocr)
        switch_layout.addStretch()
        layout.addLayout(switch_layout)

    def _on_switch(self, btn_id):
        self._show_processed = (btn_id == 1)
        if self._show_ocr:
            self._show_ocr = False
            self._btn_ocr.setChecked(False)
            self._btn_ocr.setText("显示识别文字")
        self._refresh_display()

    def _on_toggle_ocr(self):
        """切换OCR文字/图片显示"""
        self._show_ocr = self._btn_ocr.isChecked()
        if self._show_ocr:
            self._btn_ocr.setText("显示图片")
            self._show_ocr_text()
        else:
            self._btn_ocr.setText("显示识别文字")
            self._refresh_display()

    def set_image(self, image_path: str):
        """加载并显示图片"""
        self._image_path = image_path
        self._original_img = cv2.imread(image_path)
        if self._original_img is None:
            self._image_label.setText("无法加载图片")
            return
        self._processed_img = None
        self._show_processed = False
        self._show_ocr = False
        self._ocr_results = None
        self._rb_original.setChecked(True)
        self._btn_ocr.setChecked(False)
        self._btn_ocr.setEnabled(False)
        self._btn_ocr.setText("显示识别文字")
        self._refresh_display()
        self.image_loaded.emit(image_path)

    def set_processed_image(self, img: np.ndarray):
        """设置处理后的图片"""
        self._processed_img = img

    def set_ocr_results(self, ocr_results):
        """保存OCR识别结果，启用切换按钮"""
        self._ocr_results = ocr_results
        self._btn_ocr.setEnabled(bool(ocr_results))

    def _refresh_display(self):
        """刷新图片显示"""
        img = self._processed_img if (self._show_processed and self._processed_img is not None) \
            else self._original_img
        if img is None:
            return
        pixmap = self._numpy_to_pixmap(img)
        # 缩放适应面板宽度
        scaled = pixmap.scaledToWidth(
            self._scroll.viewport().width() - 20, Qt.SmoothTransformation)
        self._image_label.setPixmap(scaled)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("")

    def _show_ocr_text(self):
        """显示OCR识别结果文字"""
        if not self._ocr_results:
            self._image_label.setText("未识别到文字")
            self._image_label.setStyleSheet("color: #888; font-size: 16px;")
            return

        lines = []
        for item in self._ocr_results:
            text = item.get('text', '') if isinstance(item, dict) else str(item)
            conf = item.get('confidence', 0) if isinstance(item, dict) else 0
            lines.append(f"{text}  (置信度: {conf:.2f})")

        self._image_label.setPixmap(QPixmap())
        self._image_label.setText("\n".join(lines))
        self._image_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._image_label.setWordWrap(True)
        self._image_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._image_label.setStyleSheet(
            "color: #333; font-size: 14px; padding: 10px; "
            "font-family: 'Microsoft YaHei', 'PingFang SC', monospace;"
        )

    def _numpy_to_pixmap(self, img: np.ndarray) -> QPixmap:
        """numpy数组转QPixmap"""
        if len(img.shape) == 2:
            # 灰度图
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format_Grayscale8)
        else:
            h, w, ch = img.shape
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def get_image_path(self) -> str:
        return self._image_path

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._original_img is not None and not self._show_ocr:
            self._refresh_display()

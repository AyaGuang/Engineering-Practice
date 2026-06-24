"""ocr_eval.backends.base - OCR 模型后端抽象基类

所有具体的 OCR 模型（PaddleOCR、TrOCR、MMOCR 等）都应实现此接口，
让上层评估代码与具体模型解耦（SOLID-D：依赖抽象）。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class BaseModelBackend(ABC):
    """OCR 模型后端的统一接口"""

    # 子类必须声明唯一标识，如 "paddleocr"、"trocr"
    name: str = "base"

    @abstractmethod
    def __init__(self, model_dir: str, **kwargs: Any) -> None:
        """加载模型（子类实现具体逻辑）

        Args:
            model_dir: 模型目录（含权重与配置）
            **kwargs: 模型特定参数（device、dtype 等）
        """
        ...

    @abstractmethod
    def predict_batch(self, img_paths: list[str]) -> list[str]:
        """从文件路径批量推理

        Args:
            img_paths: 图片文件路径列表

        Returns:
            识别文本列表，与 img_paths 一一对应；失败位置为空字符串
        """
        ...

    def predict_images(self, images: list[np.ndarray]) -> list[str]:
        """从 ndarray 批量推理（用于退化评估，避免临时文件 IO）

        默认实现：写临时文件后调用 predict_batch。
        子类可重写以获得更好性能（直接传 ndarray 给模型）。

        Args:
            images: BGR ndarray 列表

        Returns:
            识别文本列表
        """
        import tempfile
        from pathlib import Path

        import cv2

        tmp_paths: list[str] = []
        for img in images:
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            tmp.close()
            cv2.imwrite(tmp.name, img)
            tmp_paths.append(tmp.name)
        try:
            return self.predict_batch(tmp_paths)
        finally:
            for p in tmp_paths:
                Path(p).unlink(missing_ok=True)

    def warmup(self) -> None:
        """模型预热（可选，子类可重写）"""
        return None

"""ocr_eval.backends.paddle_ocr - PaddleOCR 后端实现"""
from typing import Any

import numpy as np

from .base import BaseModelBackend


class PaddleOCRBackend(BaseModelBackend):
    """PaddleOCR TextRecognition 后端"""

    name = "paddleocr"

    def __init__(
        self,
        model_dir: str,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        # 延迟导入：仅在用到 PaddleOCR 时加载（避免强制依赖）
        from paddleocr import TextRecognition

        self.model_dir = model_dir

        # PaddleOCR SDK 会校验 inference.yml 里的 model_name 是否匹配
        # 如果不传 model_name，会用默认值（PP-OCRv6_medium_rec），加载其他版本会报错
        init_kwargs = {"model_dir": model_dir}
        if model_name:
            init_kwargs["model_name"] = model_name

        self.model = TextRecognition(**init_kwargs)

    def predict_batch(self, img_paths: list[str]) -> list[str]:
        if not img_paths:
            return []
        results = self.model.predict(input=img_paths, batch_size=len(img_paths))
        texts: list[str] = []
        for res in results:
            try:
                text = res.json["res"]["rec_text"]
            except (KeyError, TypeError, IndexError):
                text = ""
            texts.append(text)
        return texts

    def predict_images(self, images: list[np.ndarray]) -> list[str]:
        """直接走临时文件（PaddleOCR SDK 的输入是路径）"""
        return super().predict_images(images)

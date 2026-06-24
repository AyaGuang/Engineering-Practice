"""ocr_eval.backends.easyocr - EasyOCR 后端实现

EasyOCR 是 JaidedAI 开源的多语言 OCR，基于 PyTorch + CRNN + CTC。
覆盖 80+ 语言，安装简单（pip install easyocr），首次使用时自动下载模型。

注意：EasyOCR 默认是 detection + recognition pipeline。
本 backend 通过调整参数让裁好的单行文本图也能正确识别（合并为一段）。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from typing import Any

import numpy as np

from .base import BaseModelBackend


class EasyOCRBackend(BaseModelBackend):
    """EasyOCR 后端（ch_sim + en 双语）"""

    name = "easyocr"

    def __init__(
        self,
        model_dir: str | None = None,  # EasyOCR 自动管理模型，这里仅作占位
        langs: list[str] | None = None,
        gpu: bool = True,
        detail: int = 0,
        paragraph: bool = True,
        **kwargs: Any,
    ) -> None:
        import torch

        # 延迟导入：仅在用到时加载 easyocr
        import easyocr

        if langs is None:
            langs = ["ch_sim", "en"]  # 中文简体 + 英文

        if gpu and not torch.cuda.is_available():
            print("[warn] CUDA 不可用，EasyOCR 回退到 CPU")
            gpu = False

        self.langs = langs
        self.gpu = gpu
        self.detail = detail
        self.paragraph = paragraph

        # 首次初始化会下载模型（ch_sim + en 约 ~100MB）
        self.reader = easyocr.Reader(langs, gpu=gpu)

    def _predict_single(self, img: np.ndarray | str) -> str:
        """对单张图片识别，返回拼接后的文本"""
        # detail=0 → 只返回文本字符串列表
        # paragraph=True → 合并相邻框为一段
        results = self.reader.readtext(img, detail=self.detail, paragraph=self.paragraph)
        if not results:
            return ""
        # results 是字符串列表（detail=0 时）
        if isinstance(results[0], str):
            return " ".join(results)
        # 兼容 detail=1 的情况：(bbox, text, conf)
        return " ".join(r[1] for r in results)

    def predict_batch(self, img_paths: list[str]) -> list[str]:
        if not img_paths:
            return []
        # EasyOCR 自带 batch_size 参数，但逐张更稳定（避免 OOM）
        return [self._predict_single(p) for p in img_paths]

    def predict_images(self, images: list[np.ndarray]) -> list[str]:
        """EasyOCR 原生支持 ndarray 输入"""
        return [self._predict_single(img) for img in images]

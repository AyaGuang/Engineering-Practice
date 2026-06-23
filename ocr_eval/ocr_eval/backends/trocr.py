"""ocr_eval.backends.trocr - TrOCR 后端实现

TrOCR（Transformer-based OCR）是 Microsoft 提出的基于 encoder-decoder
transformer 的 OCR 模型，HuggingFace transformers 库提供实现。

注意：
- 官方 microsoft/trocr-base-print 是英文模型，中文识别准确率较低
- 中文场景建议使用社区微调版本（如 Shoukan/TrOCR-zh 等）
- 依赖 torch + transformers（约 2.5GB），默认不安装，按需启用
"""
from typing import Any

import numpy as np

from .base import BaseModelBackend


class TrOCRBackend(BaseModelBackend):
    """HuggingFace TrOCR 后端"""

    name = "trocr"

    def __init__(
        self,
        model_dir: str,
        device: str = "cuda",
        max_new_tokens: int = 64,
        **kwargs: Any,
    ) -> None:
        # 延迟导入：仅在用到 TrOCR 时加载 torch + transformers
        import torch
        from transformers import (
            TrOCRProcessor,
            VisionEncoderDecoderModel,
            ViTImageProcessor,
            AutoTokenizer,
        )

        self.model_dir = model_dir
        self.device = device
        self.max_new_tokens = max_new_tokens

        # 加载模型权重
        self.model = VisionEncoderDecoderModel.from_pretrained(model_dir)
        self.model.eval()

        # 加载 processor：部分社区中文 TrOCR 仓库缺少 preprocessor_config.json
        # 此时 fallback 到标准 ViTImageProcessor + 模型自带的 tokenizer
        try:
            self.processor = TrOCRProcessor.from_pretrained(model_dir)
        except (OSError, EnvironmentError):
            print(f"[warn] {model_dir} 缺少 preprocessor_config.json，使用标准 ViT image processor")
            image_processor = ViTImageProcessor(
                size={"height": 384, "width": 384},
                resample=3,  # Image.BICUBIC
            )
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.processor = TrOCRProcessor(
                image_processor=image_processor, tokenizer=tokenizer
            )

        if device.startswith("cuda") and not torch.cuda.is_available():
            print(f"[warn] CUDA 不可用，回退到 CPU")
            self.device = "cpu"

        self.model.to(self.device)

    def _generate(self, pixel_values) -> list[str]:
        import torch

        with torch.no_grad():
            generated_ids = self.model.generate(
                pixel_values, max_new_tokens=self.max_new_tokens
            )
        return self.processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )

    def predict_images(self, images: list[np.ndarray]) -> list[str]:
        """TrOCR 原生支持 ndarray 输入（通过 PIL）"""
        from PIL import Image

        # BGR (numpy) → RGB (PIL)
        pil_images = [Image.fromarray(img[:, :, ::-1]).convert("RGB") for img in images]
        pixel_values = self.processor(images=pil_images, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        return self._generate(pixel_values)

    def predict_batch(self, img_paths: list[str]) -> list[str]:
        from PIL import Image

        pil_images = [Image.open(p).convert("RGB") for p in img_paths]
        pixel_values = self.processor(images=pil_images, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        return self._generate(pixel_values)

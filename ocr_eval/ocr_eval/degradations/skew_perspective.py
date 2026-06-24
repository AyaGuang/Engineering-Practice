"""ocr_eval.degradations.skew_perspective - 小角度旋转 + 轻微透视

模拟：手持拍摄轻抖 + 纸张弯曲/不平整

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from typing import Any

import cv2
import numpy as np

from .base import BaseDegradation


class SkewPerspectiveDegradation(BaseDegradation):
    name = "skew_perspective"

    def __init__(
        self,
        max_angle: float = 5.0,            # 最大旋转角 ±度
        perspective_strength: float = 0.02, # 透视扰动强度 0-0.1
        seed: int | None = 42,              # 随机种子（可复现）
        **kwargs: Any,
    ) -> None:
        self.max_angle = max_angle
        self.perspective_strength = perspective_strength
        self.seed = seed
        # 每个 epoch 重置一次种子，保证可复现
        self._rng = np.random.default_rng(seed)

    def apply(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]

        # 1) 小角度旋转
        angle = self._rng.uniform(-self.max_angle, self.max_angle)
        M_rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        img = cv2.warpAffine(
            img, M_rot, (w, h), borderMode=cv2.BORDER_REPLICATE
        )

        # 2) 轻微透视变换（纸张不平）
        if self.perspective_strength > 0:
            src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
            offset = self.perspective_strength * min(w, h)
            dst = src + self._rng.uniform(
                -offset, offset, size=src.shape
            ).astype(np.float32)
            M_persp = cv2.getPerspectiveTransform(src, dst)
            img = cv2.warpPerspective(
                img, M_persp, (w, h), borderMode=cv2.BORDER_REPLICATE
            )

        return img

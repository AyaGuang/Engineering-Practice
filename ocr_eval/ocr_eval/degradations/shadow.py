"""ocr_eval.degradations.shadow - 随机阴影遮挡

模拟：手、笔、手机等物体在纸面上投下的条带状阴影
实现：生成带羽化边缘的随机矩形阴影，用 alpha 混合叠加到原图
"""
from typing import Any

import cv2
import numpy as np

from .base import BaseDegradation


class ShadowDegradation(BaseDegradation):
    name = "shadow"

    def __init__(
        self,
        n_shadows: int = 2,              # 阴影数量
        shadow_intensity: float = 0.55,   # 阴影最大不透明度（0-1）
        width_ratio_range: tuple[float, float] = (0.15, 0.35),  # 阴影宽度占图片宽度的比例范围
        length_ratio_range: tuple[float, float] = (0.6, 1.0),   # 阴影长度占图片对角线的比例范围
        feather: int = 35,                # 羽化半径（像素），让阴影边缘柔和
        seed: int | None = 42,
        **kwargs: Any,
    ) -> None:
        self.n_shadows = n_shadows
        self.shadow_intensity = shadow_intensity
        self.width_ratio_range = width_ratio_range
        self.length_ratio_range = length_ratio_range
        self.feather = feather
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def _random_shadow_mask(self, h: int, w: int) -> np.ndarray:
        """生成一张带羽化边缘的随机条状阴影 mask（值 0-1）"""
        # 阴影参数
        angle_deg = self._rng.uniform(0, 180)
        diag = int(np.sqrt(h * h + w * w))
        length = int(diag * self._rng.uniform(*self.length_ratio_range))
        width = max(8, int(w * self._rng.uniform(*self.width_ratio_range)))

        # 在大画布上画一个白色旋转矩形（避免旋转后不够长）
        canvas = int(diag * 1.5)
        mask = np.zeros((canvas, canvas), dtype=np.uint8)
        cx = cy = canvas // 2
        rect = ((cx, cy), (length, width), angle_deg)
        box = cv2.boxPoints(rect).astype(np.intp)
        cv2.fillConvexPoly(mask, box, 255)

        # 羽化（高斯模糊让边缘柔和）
        if self.feather > 0:
            ksize = self.feather * 2 + 1
            mask = cv2.GaussianBlur(mask, (ksize, ksize), self.feather / 2)

        # 裁剪到原尺寸（随机偏移）
        offset_x = self._rng.integers(0, canvas - w)
        offset_y = self._rng.integers(0, canvas - h)
        mask = mask[offset_y : offset_y + h, offset_x : offset_x + w]

        # 归一化到 0-1 + 按强度缩放
        return (mask.astype(np.float32) / 255.0) * self.shadow_intensity

    def apply(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        combined = np.zeros((h, w), dtype=np.float32)
        for _ in range(self.n_shadows):
            combined = np.maximum(combined, self._random_shadow_mask(h, w))

        # img × (1 - shadow_mask)：阴影处变暗
        out = img.astype(np.float32) * (1.0 - combined[..., None])
        return out.clip(0, 255).astype(np.uint8)

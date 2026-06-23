"""ocr_eval.degradations.motion_blur - 方向性运动模糊

模拟：手持拍摄时相机/手机抖动产生的方向性模糊
与高斯模糊的区别：运动模糊沿单一方向扩散，更贴近真实拍摄抖动
实现：构造线性卷积核并按随机角度旋转，然后卷积到图像
"""
from typing import Any

import cv2
import numpy as np

from .base import BaseDegradation


class MotionBlurDegradation(BaseDegradation):
    name = "motion_blur"

    def __init__(
        self,
        kernel_size: int = 7,           # 运动模糊核大小（奇数，越大越模糊）
        angle_range: tuple[float, float] = (0.0, 360.0),  # 运动方向角度范围
        seed: int | None = 42,
        **kwargs: Any,
    ) -> None:
        # 保证 kernel_size 为奇数
        if kernel_size % 2 == 0:
            kernel_size += 1
        self.kernel_size = kernel_size
        self.angle_range = angle_range
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def _build_motion_kernel(self) -> np.ndarray:
        """构造一个带随机方向的运动模糊核"""
        k = self.kernel_size

        # 水平方向的线性核：中心一行全为 1/k
        kernel = np.zeros((k, k), dtype=np.float32)
        kernel[k // 2, :] = 1.0 / k

        # 按随机角度旋转核
        angle = self._rng.uniform(*self.angle_range)
        M = cv2.getRotationMatrix2D((k / 2, k / 2), angle, 1.0)
        kernel = cv2.warpAffine(
            kernel,
            M,
            (k, k),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )

        # 归一化，保证卷积后亮度不变
        s = kernel.sum()
        if s > 0:
            kernel = kernel / s
        return kernel

    def apply(self, img: np.ndarray) -> np.ndarray:
        kernel = self._build_motion_kernel()
        return cv2.filter2D(img, -1, kernel)

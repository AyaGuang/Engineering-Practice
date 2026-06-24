"""ocr_eval.degradations.base - 图像退化抽象基类

所有具体的退化（低光照、模糊、旋转等）都实现此接口，
让评估代码可以灵活组合不同的退化（SOLID-O：对扩展开放）。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class BaseDegradation(ABC):
    """图像退化的统一接口"""

    # 子类必须声明唯一标识，如 "low_light"
    name: str = "base"

    @abstractmethod
    def __init__(self, **kwargs: Any) -> None:
        """初始化退化参数"""
        ...

    @abstractmethod
    def apply(self, img: np.ndarray) -> np.ndarray:
        """对单张图片应用退化

        Args:
            img: BGR 格式的 ndarray (H, W, 3)

        Returns:
            退化后的 BGR ndarray（同 shape）
        """
        ...

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """便捷调用：degradation(img) 等价于 degradation.apply(img)"""
        return self.apply(img)

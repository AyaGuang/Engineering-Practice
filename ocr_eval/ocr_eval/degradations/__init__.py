"""ocr_eval.degradations - 图像退化注册表

通过名称获取退化实例。返回 None 表示"不退化"（clean）。
"""
from typing import Optional, Type

from .base import BaseDegradation
from .low_light import LowLightDegradation
from .motion_blur import MotionBlurDegradation
from .shadow import ShadowDegradation
from .skew_perspective import SkewPerspectiveDegradation

DEGRADATION_REGISTRY: dict[str, Type[BaseDegradation]] = {
    "low_light": LowLightDegradation,
    "shadow": ShadowDegradation,
    "motion_blur": MotionBlurDegradation,
    "skew_perspective": SkewPerspectiveDegradation,
}


def get_degradation(name: Optional[str]) -> Optional[BaseDegradation]:
    """工厂方法：按名称创建退化实例。

    Args:
        name: 退化名称；None / "clean" 返回 None（不退化）

    Returns:
        退化实例 或 None
    """
    if name is None or name == "clean":
        return None
    if name not in DEGRADATION_REGISTRY:
        available = ", ".join(DEGRADATION_REGISTRY.keys())
        raise ValueError(f"未知退化 '{name}'。可选: {available}")
    return DEGRADATION_REGISTRY[name]()


def list_degradations() -> list[str]:
    """列出所有已注册的退化名称"""
    return list(DEGRADATION_REGISTRY.keys())


__all__ = [
    "BaseDegradation",
    "LowLightDegradation",
    "ShadowDegradation",
    "MotionBlurDegradation",
    "SkewPerspectiveDegradation",
    "DEGRADATION_REGISTRY",
    "get_degradation",
    "list_degradations",
]

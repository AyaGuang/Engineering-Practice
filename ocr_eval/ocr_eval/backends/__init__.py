"""ocr_eval.backends - OCR 模型后端注册表

通过名称（如 "paddleocr"、"trocr"、"easyocr"）获取 backend 类，
让上层代码与具体模型解耦。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from typing import Type

from .base import BaseModelBackend
from .easyocr import EasyOCRBackend
from .paddle_ocr import PaddleOCRBackend
from .trocr import TrOCRBackend

BACKEND_REGISTRY: dict[str, Type[BaseModelBackend]] = {
    "paddleocr": PaddleOCRBackend,
    "trocr": TrOCRBackend,
    "easyocr": EasyOCRBackend,
}


def get_backend(name: str) -> Type[BaseModelBackend]:
    """工厂方法：按名称获取 backend 类"""
    if name not in BACKEND_REGISTRY:
        available = ", ".join(BACKEND_REGISTRY.keys())
        raise ValueError(f"未知 backend '{name}'。可选: {available}")
    return BACKEND_REGISTRY[name]


def list_backends() -> list[str]:
    """列出所有已注册的 backend 名称"""
    return list(BACKEND_REGISTRY.keys())


__all__ = [
    "BaseModelBackend",
    "PaddleOCRBackend",
    "TrOCRBackend",
    "EasyOCRBackend",
    "BACKEND_REGISTRY",
    "get_backend",
    "list_backends",
]

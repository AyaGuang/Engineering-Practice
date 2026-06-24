"""ocr_eval.visualize - 退化效果可视化

生成 before/after 对比图，便于肉眼检查退化参数是否合理。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
from pathlib import Path

import cv2
import numpy as np


def save_before_after(
    original: np.ndarray,
    degraded: np.ndarray,
    out_path: str | Path,
    label_original: str = "original",
    label_degraded: str = "degraded",
) -> str:
    """保存原图与退化图的横向拼接对比图

    Args:
        original: 原图 BGR ndarray
        degraded: 退化后 BGR ndarray
        out_path: 输出 PNG 路径
        label_original: 原图标签
        label_degraded: 退化图标签

    Returns:
        实际写入的路径
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    h1, w1 = original.shape[:2]
    h2, w2 = degraded.shape[:2]
    h = max(h1, h2)

    # 高度对齐
    if h1 != h:
        original = cv2.resize(original, (int(w1 * h / h1), h))
    if h2 != h:
        degraded = cv2.resize(degraded, (int(w2 * h / h2), h))

    gap = np.full((h, 10, 3), 255, dtype=np.uint8)  # 白色分隔条
    combined = np.hstack([original, gap, degraded])

    # 顶部加标签条
    bar_h = 24
    bar = np.full((bar_h, combined.shape[1], 3), 255, dtype=np.uint8)
    cv2.putText(
        bar, label_original, (8, 17),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
    )
    cv2.putText(
        bar, label_degraded, (original.shape[1] + 20, 17),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
    )

    final = np.vstack([bar, combined])
    cv2.imwrite(str(out_path), final)
    return str(out_path)


def save_degradation_samples(
    img_paths: list[str],
    degradation_fn,
    out_dir: str | Path,
    degradation_name: str,
    n_samples: int = 5,
) -> list[str]:
    """对多张图应用退化并保存对比图

    Args:
        img_paths: 原图路径列表
        degradation_fn: 退化实例（有 .apply 方法）或 None
        out_dir: 输出目录
        degradation_name: 退化名称（用于文件命名）
        n_samples: 保存多少张

    Returns:
        生成的对比图路径列表
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for i, p in enumerate(img_paths[:n_samples]):
        original = cv2.imread(p)
        if original is None:
            continue
        if degradation_fn is None:
            continue
        degraded = degradation_fn.apply(original)
        out_path = out_dir / f"{degradation_name}_sample_{i:03d}.png"
        save_before_after(
            original, degraded, out_path,
            label_original="original",
            label_degraded=degradation_name,
        )
        saved.append(str(out_path))
    return saved

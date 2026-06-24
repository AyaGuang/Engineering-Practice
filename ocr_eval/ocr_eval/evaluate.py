"""ocr_eval.evaluate - 评估主流程（支持 backend + degradation）

通过依赖注入接收 backend 名称与退化名称，让评估流程与具体模型/退化解耦。

* create by 林文光
* copyright USTC
* 2026.06.23
"""
import time
from pathlib import Path

import cv2
import numpy as np

from .metrics import compute_metrics


def load_val_list(label_file: str | Path) -> list[tuple[str, str]]:
    """读取 PaddleOCR 评估格式的标注文件

    每行：图片相对路径 <TAB> 标签文字
    """
    pairs: list[tuple[str, str]] = []
    with open(label_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            img_rel, text = line.split("\t", 1)
            pairs.append((img_rel, text))
    return pairs


def run_evaluation(
    backend_name: str,
    data_dir: str,
    label_file: str,
    model_dir: str | None = None,
    batch_size: int = 32,
    limit: int = 0,
    degradation: str | None = None,
    degradation_kwargs: dict | None = None,
    save_samples: int = 0,
    samples_dir: str | None = None,
    backend_kwargs: dict | None = None,
) -> dict:
    """运行评估（支持模型 × 退化组合）

    Args:
        backend_name: 模型后端名称（"paddleocr" / "trocr" / "easyocr" / "doctr"）
        model_dir: 推理模型目录（部分 backend 可为 None，如 easyocr）
        data_dir: 数据根目录
        label_file: 标注文件
        batch_size: 批大小
        limit: 限制评估样本数（0 = 全量）
        degradation: 退化名称（None / "clean" / "low_light" / ...）
        degradation_kwargs: 退化参数（覆盖默认值）
        save_samples: 保存多少张退化对比图（0 = 不保存）
        samples_dir: 对比图输出目录
        backend_kwargs: 传递给 backend 初始化的额外参数（如 model_name）

    Returns:
        评估结果 dict（含 backend/degradation/acc/norm_edit_dis/...）
    """
    # 延迟导入：避免加载未安装的依赖
    from .backends import get_backend
    from .degradations import get_degradation

    BackendCls = get_backend(backend_name)
    # 合并 model_dir 和额外参数
    init_kwargs = dict(backend_kwargs or {})
    if model_dir is not None:
        init_kwargs["model_dir"] = model_dir
    backend = BackendCls(**init_kwargs)

    degradation_fn = get_degradation(degradation)
    # 如果传了 degradation_kwargs，用它们重新构造退化实例
    if degradation_fn is not None and degradation_kwargs:
        from .degradations import DEGRADATION_REGISTRY

        DegradationCls = DEGRADATION_REGISTRY[degradation]
        degradation_fn = DegradationCls(**degradation_kwargs)

    pairs = load_val_list(label_file)
    if limit > 0:
        pairs = pairs[:limit]

    img_paths = [str(Path(data_dir) / rel) for rel, _ in pairs]
    gts = [text for _, text in pairs]

    # 保存退化对比图
    saved_sample_paths: list[str] = []
    if save_samples > 0 and samples_dir:
        from .visualize import save_degradation_samples

        if degradation_fn is None:
            # clean 不需要对比图
            pass
        else:
            saved_sample_paths = save_degradation_samples(
                img_paths=img_paths,
                degradation_fn=degradation_fn,
                out_dir=samples_dir,
                degradation_name=degradation or "degradation",
                n_samples=save_samples,
            )

    preds: list[str] = []
    t0 = time.time()

    for batch_start in range(0, len(img_paths), batch_size):
        batch_end = min(batch_start + batch_size, len(img_paths))
        batch_paths = img_paths[batch_start:batch_end]

        try:
            if degradation_fn is not None:
                # 退化模式：读图 → 应用退化 → 传 ndarray 给 backend
                batch_imgs = []
                for p in batch_paths:
                    img = cv2.imread(p)
                    if img is None:
                        img = np.zeros((32, 32, 3), dtype=np.uint8)
                    else:
                        img = degradation_fn.apply(img)
                    batch_imgs.append(img)
                batch_preds = backend.predict_images(batch_imgs)
            else:
                # clean 模式：直接传路径
                batch_preds = backend.predict_batch(batch_paths)

            preds.extend(batch_preds)
        except Exception as e:
            print(f"  [warn] batch {batch_start} 失败: {e}，降级单张")
            for p in batch_paths:
                try:
                    if degradation_fn is not None:
                        img = cv2.imread(p)
                        if img is not None:
                            img = degradation_fn.apply(img)
                            pred = backend.predict_images([img])[0]
                        else:
                            pred = ""
                    else:
                        pred = backend.predict_batch([p])[0]
                except Exception:
                    pred = "<error>"
                preds.append(pred)

        elapsed = time.time() - t0
        done = batch_end
        fps = done / elapsed if elapsed > 0 else 0
        if (batch_start // batch_size) % 10 == 0:
            print(
                f"  进度 {done}/{len(img_paths)}  "
                f"elapsed={elapsed:.1f}s  fps={fps:.1f}"
            )

    elapsed = time.time() - t0
    fps = len(img_paths) / elapsed if elapsed > 0 else 0

    metrics = compute_metrics(preds, gts)

    return {
        "backend": backend_name,
        "model_dir": str(model_dir) if model_dir else None,
        "degradation": degradation or "clean",
        "data_dir": str(data_dir),
        "label_file": str(label_file),
        "num_samples": len(gts),
        "batch_size": batch_size,
        "limit": limit,
        "elapsed_sec": elapsed,
        "fps": fps,
        "saved_samples": saved_sample_paths,
        **metrics,
    }

"""ocr_eval.metrics - 评估指标计算

提供 OCR 识别任务的核心指标：
- acc: 完全匹配准确率
- norm_edit_dis: 归一化编辑距离（字符级相似度）
- 长度分布准确率
"""
from collections import defaultdict
from typing import Iterable


def edit_distance(s1: str, s2: str) -> int:
    """计算两个字符串的 Levenshtein 编辑距离"""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        cur = [i + 1]
        for j, c2 in enumerate(s2):
            cur.append(min(prev[j + 1] + 1, cur[j] + 1, prev[j] + (c1 != c2)))
        prev = cur
    return prev[-1]


def norm_edit_dis(pred: str, gt: str) -> float:
    """归一化编辑距离（1 = 完美匹配，0 = 完全不同）"""
    m = max(len(pred), len(gt))
    if m == 0:
        return 1.0
    return 1.0 - edit_distance(pred, gt) / m


def compute_metrics(
    preds: Iterable[str],
    gts: Iterable[str],
    length_bucket_size: int = 5,
    max_bucket: int = 25,
) -> dict:
    """批量计算 acc / norm_edit_dis / 长度分布

    Args:
        preds: 预测文本列表
        gts: 真实标签列表
        length_bucket_size: 长度分桶大小（默认 5）
        max_bucket: 最大桶值（超过的归入此桶）

    Returns:
        {
            "num_samples": int,
            "acc": float,
            "norm_edit_dis": float,
            "length_distribution": {bucket: {"n", "correct", "acc"}},
            "wrong_samples": [{"gt", "pred", "ned"}, ...],  # 按 ned 升序
        }
    """
    preds = list(preds)
    gts = list(gts)
    assert len(preds) == len(gts), f"长度不一致: preds={len(preds)}, gts={len(gts)}"

    n = len(gts)
    if n == 0:
        return {
            "num_samples": 0,
            "acc": 0.0,
            "norm_edit_dis": 0.0,
            "length_distribution": {},
            "wrong_samples": [],
        }

    correct = 0
    total_ned = 0.0
    wrong_samples = []
    buckets: dict[int, list[bool]] = defaultdict(list)

    for pred, gt in zip(preds, gts):
        is_correct = pred == gt
        if is_correct:
            correct += 1
        else:
            ned = norm_edit_dis(pred, gt)
            total_ned += ned
            wrong_samples.append({"gt": gt, "pred": pred, "ned": ned})

        # 正确样本 ned=1.0
        if is_correct:
            total_ned += 1.0

        bucket = min(len(gt) // length_bucket_size * length_bucket_size, max_bucket)
        buckets[bucket].append(is_correct)

    wrong_samples.sort(key=lambda x: x["ned"])

    length_distribution = {
        str(b): {
            "n": len(results),
            "correct": sum(results),
            "acc": sum(results) / len(results) if results else 0.0,
        }
        for b, results in sorted(buckets.items())
    }

    return {
        "num_samples": n,
        "acc": correct / n,
        "norm_edit_dis": total_ned / n,
        "length_distribution": length_distribution,
        "wrong_samples": wrong_samples,
    }

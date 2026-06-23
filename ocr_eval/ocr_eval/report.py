"""ocr_eval.report - 评估报告输出

控制台友好输出 + JSON 持久化。
"""
import json
from pathlib import Path


def print_report(result: dict) -> None:
    """打印评估结果到控制台"""
    print()
    print("=" * 60)
    print("评估结果")
    print("=" * 60)
    print(f"模型目录     : {result.get('model_dir', 'N/A')}")
    print(f"样本总数     : {result['num_samples']}")
    print(f"批大小       : {result['batch_size']}")
    print(f"完全正确     : {int(result['acc'] * result['num_samples'])}")
    print(f"acc          : {result['acc']:.4f}  ({result['acc']*100:.2f}%)")
    print(f"norm_edit_dis: {result['norm_edit_dis']:.4f}  ({result['norm_edit_dis']*100:.2f}%)")
    print(f"总耗时       : {result['elapsed_sec']:.1f}s")
    print(f"fps          : {result['fps']:.2f}")

    length_dist = result.get("length_distribution", {})
    if length_dist:
        print()
        print("各长度区间准确率:")
        for bucket, info in length_dist.items():
            n = info["n"]
            c = info["correct"]
            acc = info["acc"]
            print(f"  长度 {bucket:>3s}: {c:5d}/{n:5d} = {acc:.4f}")

    wrong_samples = result.get("wrong_samples", [])
    print()
    print(f"错误样本总数: {len(wrong_samples)}")
    if wrong_samples:
        print()
        print(f"最差 10 个样本（ned 最低）:")
        for s in wrong_samples[:10]:
            gt = s["gt"]
            pred = s["pred"]
            ned = s["ned"]
            print(f"  GT={gt!r:30s}  PRED={pred!r:30s}  ned={ned:.2f}")


def save_report(result: dict, path: str | Path, max_wrong_samples: int = 50) -> str:
    """保存完整报告到 JSON 文件

    Args:
        result: 评估结果 dict
        path: 输出 JSON 路径
        max_wrong_samples: 最多保存多少错误样本（避免文件过大）

    Returns:
        实际写入的路径
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 复制一份，截断错误样本
    report = dict(result)
    if "wrong_samples" in report:
        report["wrong_samples"] = report["wrong_samples"][:max_wrong_samples]

    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def print_convert_summary(stats: dict) -> None:
    """打印转换结果摘要"""
    print()
    print("=" * 60)
    print("转换结果")
    print("=" * 60)
    print(f"parquet 路径       : {stats['parquet_path']}")
    print(f"输出目录           : {stats['out_dir']}")
    print(f"parquet 总样本     : {stats['total_in_parquet']}")
    print(f"本次处理上限       : {stats['processed_requested']}")
    print(f"有效样本           : {stats['valid']}")
    print(f"跳过（空标签）     : {stats['skipped_empty']}")
    print(f"跳过（超长 >{25}） : {stats['skipped_too_long']}")
    print(f"跳过（OOV 字典外） : {stats['skipped_oov']}")
    print(f"字典大小           : {stats['dict_size']}")
    if stats["top_oov_chars"]:
        print(f"  Top 10 OOV 字符  : {stats['top_oov_chars']}")
    print()
    print(f"图片目录           : {stats['image_dir']}")
    print(f"标注文件           : {stats['label_file']}")

"""ocr_eval.scripts.run_convert - CLI 入口：parquet → PaddleOCR 评估格式

用法:
    # 试运行（前 100 条）
    python scripts/run_convert.py --demo

    # 全量转换
    python scripts/run_convert.py

    # 自定义路径
    python scripts/run_convert.py \\
        --parquet data/custom.parquet \\
        --out_dir output/custom \\
        --dict /path/to/paddleocr/utils/dict/ppocrv6_dict.txt
"""
import argparse
import sys
from pathlib import Path

# 将父目录加入 sys.path，让 `from ocr_eval.convert import ...` 能找到包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocr_eval.convert import convert_parquet
from ocr_eval.report import print_convert_summary


def main():
    ap = argparse.ArgumentParser(description="parquet → PaddleOCR 评估格式 转换")
    ap.add_argument(
        "--parquet",
        default="data/val-00000-of-00001-5c426e00156faaab.parquet",
        help="parquet 文件路径",
    )
    ap.add_argument(
        "--out_dir",
        default="output/parquet_val",
        help="输出目录（图片 + val_list.txt）",
    )
    ap.add_argument(
        "--dict",
        default="../PaddleOCR/ppocr/utils/dict/ppocrv6_dict.txt",
        help="字典文件路径（用于 OOV 检查）",
    )
    ap.add_argument("--demo", action="store_true", help="仅处理前 100 条")
    ap.add_argument("--limit", type=int, default=0, help="处理前 N 条（0 = 全量）")
    ap.add_argument("--max_text_length", type=int, default=25, help="最大标签长度")
    args = ap.parse_args()

    limit = 100 if args.demo else args.limit

    print("=" * 60)
    print("parquet → PaddleOCR 转换")
    print("=" * 60)
    print(f"parquet : {args.parquet}")
    print(f"out_dir : {args.out_dir}")
    print(f"dict    : {args.dict}")
    print(f"limit   : {limit if limit else '全量'}")
    print()

    dict_path = args.dict if args.dict and Path(args.dict).exists() else None
    if dict_path is None and args.dict:
        print(f"[warn] 字典不存在: {args.dict}，跳过 OOV 检查")

    stats = convert_parquet(
        parquet_path=args.parquet,
        out_dir=args.out_dir,
        dict_path=dict_path,
        limit=limit,
        max_text_length=args.max_text_length,
    )
    print_convert_summary(stats)


if __name__ == "__main__":
    main()

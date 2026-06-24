"""ocr_eval.scripts.run_evaluate - CLI 入口：评估 PaddleOCR 识别能力

用法:
    # 单模型 × clean
    python scripts/run_evaluate.py --backend paddleocr --limit 1000

    # 单模型 × 低光照
    python scripts/run_evaluate.py --backend paddleocr --degradation low_light

    # 含可视化对比图
    python scripts/run_evaluate.py --degradation blur_compress --save_samples 10

* create by 林文光
* copyright USTC
* 2026.06.23
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocr_eval.evaluate import run_evaluation
from ocr_eval.report import print_report, save_report


def main():
    ap = argparse.ArgumentParser(description="OCR 模型识别能力评估")
    ap.add_argument(
        "--backend",
        default="paddleocr",
        choices=["paddleocr", "trocr", "easyocr"],
        help="模型后端",
    )
    ap.add_argument(
        "--model_dir",
        default="../PaddleOCR/models/PP-OCRv6_medium_rec",
        help="模型目录",
    )
    ap.add_argument(
        "--model_name",
        default=None,
        help="模型名（PaddleOCR 多版本时必需，如 PP-OCRv5_server_rec）",
    )
    ap.add_argument(
        "--display_name",
        default=None,
        help="展示名称（写入报告，用于矩阵对比时区分同 backend 的不同模型）",
    )
    ap.add_argument("--data_dir", default="output/parquet_val")
    ap.add_argument("--label_file", default="output/parquet_val/val_list.txt")
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--degradation",
        default=None,
        help="退化名称（clean/low_light/blur_compress/skew_perspective）",
    )
    ap.add_argument(
        "--save_samples",
        type=int,
        default=0,
        help="保存多少张退化前后对比图（0 = 不保存）",
    )
    ap.add_argument(
        "--samples_dir",
        default=None,
        help="对比图输出目录（默认 output/samples/<degradation>/）",
    )
    ap.add_argument(
        "--report",
        default="output/reports/eval_report.json",
    )
    args = ap.parse_args()

    samples_dir = args.samples_dir
    if samples_dir is None and args.save_samples > 0 and args.degradation:
        samples_dir = f"output/samples/{args.degradation}"

    print("=" * 60)
    print("OCR 识别能力评估")
    print("=" * 60)
    print(f"backend     : {args.backend}")
    print(f"模型目录    : {args.model_dir}")
    print(f"退化        : {args.degradation or 'clean'}")
    print(f"批大小      : {args.batch_size}")
    print(f"限制        : {args.limit if args.limit else '全量'}")
    print(f"报告路径    : {args.report}")
    if samples_dir:
        print(f"对比图      : {samples_dir} (共 {args.save_samples} 张)")
    print()

    # 不对 model_dir 做本地路径检查：
    # - PaddleOCR/EasyOCR 可能用空路径或自动管理
    # - TrOCR 可用 HuggingFace 模型 ID（如 "microsoft/trocr-base-print"）
    # 让具体 backend 在初始化时处理路径错误，能给出更精确的报错

    if not Path(args.label_file).exists():
        print(f"[error] 标注文件不存在: {args.label_file}")
        print("        请先运行: python scripts/run_convert.py")
        sys.exit(1)

    # 构造 backend 初始化参数
    backend_kwargs: dict = {}
    if args.model_dir:
        backend_kwargs["model_dir"] = args.model_dir
    if args.model_name:
        backend_kwargs["model_name"] = args.model_name

    result = run_evaluation(
        backend_name=args.backend,
        data_dir=args.data_dir,
        label_file=args.label_file,
        batch_size=args.batch_size,
        limit=args.limit,
        degradation=args.degradation,
        save_samples=args.save_samples,
        samples_dir=samples_dir,
        backend_kwargs=backend_kwargs,
    )

    # 写入展示元信息（用于矩阵对比时区分模型）
    if args.model_name:
        result["model_name"] = args.model_name
    if args.display_name:
        result["display_name"] = args.display_name

    print_report(result)

    report_path = save_report(result, args.report)
    print()
    print(f"报告已保存: {report_path}")
    if result.get("saved_samples"):
        print(f"对比图已保存（共 {len(result['saved_samples'])} 张）")


if __name__ == "__main__":
    main()

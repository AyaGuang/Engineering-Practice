"""ocr_eval.scripts.run_compare - 多模型对比（不退化）

简化版的矩阵评估：只跑 clean，对比多个模型。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocr_eval.compare import load_yaml_configs, print_matrix_table
from ocr_eval.evaluate import run_evaluation
from ocr_eval.report import save_report


def main():
    ap = argparse.ArgumentParser(description="多模型对比（clean 数据集）")
    ap.add_argument("--models_dir", default="configs/models")
    ap.add_argument("--data_dir", default="output/parquet_val")
    ap.add_argument("--label_file", default="output/parquet_val/val_list.txt")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--reports_dir", default="output/reports")
    args = ap.parse_args()

    models = load_yaml_configs(Path(args.models_dir))
    if not models:
        print(f"[error] 未找到模型配置: {args.models_dir}")
        sys.exit(1)

    results = []
    for cfg in models:
        name = cfg.get("name", Path(cfg["__file__"]).stem)
        print(f"\n>>> 评估 {name}")
        try:
            result = run_evaluation(
                backend_name=cfg["backend"],
                model_dir=cfg["model_dir"],
                data_dir=args.data_dir,
                label_file=args.label_file,
                batch_size=cfg.get("batch_size", args.batch_size),
                limit=args.limit,
            )
            result["backend"] = cfg["backend"]
            result["model_name"] = name
            result["degradation"] = "clean"
            save_report(result, Path(args.reports_dir) / name / "eval_report.json")
            results.append(result)
        except Exception as e:
            print(f"[error] {name} 评估失败: {e}")

    print_matrix_table(results)


if __name__ == "__main__":
    main()

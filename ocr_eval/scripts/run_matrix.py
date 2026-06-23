"""ocr_eval.scripts.run_matrix - 模型 × 退化 矩阵评估

扫描 configs/models/ 与 configs/degradations/ 下的 yaml 配置，
自动跑所有组合，输出矩阵报告。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ocr_eval.compare import load_yaml_configs, print_matrix_table, save_matrix_report
from ocr_eval.evaluate import run_evaluation


def main():
    ap = argparse.ArgumentParser(description="模型 × 退化 矩阵评估")
    ap.add_argument("--models_dir", default="configs/models")
    ap.add_argument("--degradations_dir", default="configs/degradations")
    ap.add_argument("--data_dir", default="output/parquet_val")
    ap.add_argument("--label_file", default="output/parquet_val/val_list.txt")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument(
        "--reports_dir",
        default="output/reports",
        help="报告根目录（每个组合一个子目录）",
    )
    ap.add_argument(
        "--matrix_report",
        default="output/reports/matrix_report.json",
        help="矩阵汇总报告路径",
    )
    ap.add_argument("--save_samples", type=int, default=0)
    args = ap.parse_args()

    models = load_yaml_configs(Path(args.models_dir))
    degradations = load_yaml_configs(Path(args.degradations_dir))

    if not models:
        print(f"[error] 未找到模型配置: {args.models_dir}")
        sys.exit(1)

    # 退化列表：始终包含 clean（None），再加上配置中的
    deg_list = [None]  # clean
    for cfg in degradations:
        deg_list.append(cfg)

    print("=" * 80)
    print("矩阵评估")
    print("=" * 80)
    print(f"模型数: {len(models)}")
    print(f"退化数: {len(deg_list)} (含 clean)")
    print(f"组合总数: {len(models) * len(deg_list)}")
    print()

    results = []
    for model_cfg in models:
        backend = model_cfg["backend"]
        model_dir = model_cfg.get("model_dir")  # 某些 backend（如 easyocr）不需要
        model_name_cfg = model_cfg.get("model_name")  # PaddleOCR 需要
        model_name = model_cfg.get("name", Path(model_cfg["__file__"]).stem)
        model_batch = model_cfg.get("batch_size", args.batch_size)

        for deg_cfg in deg_list:
            if deg_cfg is None:
                deg_name = "clean"
                deg_kwargs = {}
            else:
                deg_name = deg_cfg.get("name", deg_cfg.get("__file__", "unknown"))
                # 去掉 name 和 __file__，剩下都是退化参数
                deg_kwargs = {
                    k: v for k, v in deg_cfg.items() if k not in ("name", "__file__")
                }

            combo_name = f"{model_name}__{deg_name}"
            print(f"\n>>> 评估 {combo_name}")

            try:
                # 构建 backend 初始化参数
                backend_kwargs = {}
                if model_dir:
                    backend_kwargs["model_dir"] = model_dir
                if model_name_cfg:
                    backend_kwargs["model_name"] = model_name_cfg

                result = run_evaluation(
                    backend_name=backend,
                    data_dir=args.data_dir,
                    label_file=args.label_file,
                    batch_size=model_batch,
                    limit=args.limit,
                    degradation=(None if deg_cfg is None else deg_name),
                    degradation_kwargs=deg_kwargs,
                    save_samples=args.save_samples,
                    samples_dir=f"output/samples/{deg_name}",
                    backend_kwargs=backend_kwargs,
                )
                result["backend"] = backend
                result["model_name"] = model_name
                result["display_name"] = model_cfg.get("display_name") or model_name
                result["degradation"] = deg_name

                # 保存单组合报告
                combo_report_dir = Path(args.reports_dir) / combo_name
                from ocr_eval.report import save_report

                save_report(result, combo_report_dir / "eval_report.json")

                results.append(result)
            except Exception as e:
                print(f"[error] {combo_name} 评估失败: {e}")

    print_matrix_table(results)
    matrix_path = save_matrix_report(results, args.matrix_report)
    print()
    print(f"矩阵报告已保存: {matrix_path}")


if __name__ == "__main__":
    main()

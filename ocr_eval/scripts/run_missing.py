"""扫描 reports/ 目录，找出 num_samples != 10000 的组合，自动补跑

* create by 林文光
* copyright USTC
* 2026.06.23
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
TARGET_N = 10000

# 所有应该存在的组合（从 configs 推断）
import yaml


def get_all_combos():
    """从 configs/ 推断所有组合"""
    models_dir = ROOT / "configs" / "models"
    degs_dir = ROOT / "configs" / "degradations"

    models = []
    for yml in sorted(models_dir.glob("*.yaml")):
        cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
        cfg["__file__"] = yml.stem
        models.append(cfg)

    degs = [None]  # clean
    for yml in sorted(degs_dir.glob("*.yaml")):
        cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
        degs.append(cfg.get("name", yml.stem))

    combos = []
    for m in models:
        model_stem = m["__file__"]
        for d in degs:
            deg_name = "clean" if d is None else d
            combo_dir = f"{model_stem}__{deg_name}"
            combos.append((m, deg_name, combo_dir))
    return combos


def check_existing(combo_dir):
    """检查某组合的报告是否已是目标样本数"""
    f = ROOT / "output" / "reports" / combo_dir / "eval_report.json"
    if not f.exists():
        return False, 0
    import json
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
        n = r.get("num_samples", 0)
        return n == TARGET_N, n
    except Exception:
        return False, 0


def run_one(model_cfg, degradation, combo_dir):
    """跑单个组合"""
    report_path = ROOT / "output" / "reports" / combo_dir / "eval_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    backend = model_cfg["backend"]
    print(f"\n{'='*60}")
    print(f"补跑 {combo_dir}")
    print(f"  backend={backend}, degradation={degradation}", flush=True)

    cmd = [
        sys.executable, "-u", str(ROOT / "scripts" / "run_evaluate.py"),
        "--backend", backend,
        "--degradation", degradation,
        "--limit", str(TARGET_N),
        "--batch_size", "32",
        "--report", str(report_path),
    ]
    # 传 model_dir、model_name、display_name（PaddleOCR 多版本必需）
    if model_cfg.get("model_dir"):
        cmd += ["--model_dir", model_cfg["model_dir"]]
    if model_cfg.get("model_name"):
        cmd += ["--model_name", model_cfg["model_name"]]
    if model_cfg.get("display_name"):
        cmd += ["--display_name", model_cfg["display_name"]]

    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode


def main():
    combos = get_all_combos()
    print(f"扫描 {len(combos)} 个组合，目标样本数: {TARGET_N}")

    missing = []
    for m, deg, combo in combos:
        ok, n = check_existing(combo)
        status = "OK" if ok else f"MISSING (n={n})"
        print(f"  {combo}: {status}")
        if not ok:
            missing.append((m, deg, combo))

    if not missing:
        print("\n所有组合都已是目标样本数，无需补跑")
    else:
        print(f"\n需补跑 {len(missing)} 个组合")
        for m, deg, combo in missing:
            run_one(m, deg, combo)

    # 合并并打印
    print(f"\n{'='*60}\n合并所有报告\n{'='*60}", flush=True)
    sys.path.insert(0, str(ROOT))
    from ocr_eval.compare import (
        apply_display_names,
        load_reports,
        print_matrix_table,
        save_matrix_report,
    )

    results = load_reports(ROOT / "output" / "reports")
    results_10k = [r for r in results if r.get("num_samples") == TARGET_N]
    results_10k = apply_display_names(results_10k)
    print(f"\n共 {len(results)} 份报告，其中 {TARGET_N} 条: {len(results_10k)} 份")
    print_matrix_table(results_10k)
    save_matrix_report(results_10k, ROOT / "output" / "reports" / "matrix_report.json")
    print(f"\n矩阵报告已保存", flush=True)


if __name__ == "__main__":
    main()

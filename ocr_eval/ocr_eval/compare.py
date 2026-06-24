"""ocr_eval.compare - 多模型/多退化对比汇总

* create by 林文光
* copyright USTC
* 2026.06.23
"""
import json
from pathlib import Path
from typing import Optional

import yaml


def load_yaml_configs(config_dir: str | Path) -> list[dict]:
    """加载目录下所有 yaml 配置

    Args:
        config_dir: yaml 配置目录

    Returns:
        配置 dict 列表，每个 dict 额外含 '__file__' 字段
    """
    config_dir = Path(config_dir)
    if not config_dir.exists():
        return []
    configs = []
    for yml in sorted(config_dir.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
            cfg["__file__"] = str(yml)
            configs.append(cfg)
        except Exception as e:
            print(f"[warn] 跳过 {yml}: {e}")
    return configs


def _row_id(r: dict) -> str:
    """行标识：优先 display_name，其次 model_name，最后 backend"""
    return r.get("display_name") or r.get("model_name") or r.get("backend", "?")


def apply_display_names(results: list[dict], configs_dir: str | Path = "configs/models") -> list[dict]:
    """从 configs/models/*.yaml 加载多种 key → display_name 映射，
    为已有 results 补上 display_name 字段（用于旧 json 报告）。

    映射策略：
    1. 优先按 model_name / name / 文件名 stem 精确匹配
    2. 退化到 backend 匹配（仅当该 backend 只对应唯一 display_name 时，
       例如 easyocr 只有一个模型，但 paddleocr 有 v5+v5 不能用此退化）

    Args:
        results: 评估结果列表
        configs_dir: 模型 yaml 配置目录

    Returns:
        补全 display_name 后的 results（原地修改）
    """
    configs = load_yaml_configs(configs_dir)

    # 1. 精确键映射（model_name / name / stem → display_name）
    key_mapping: dict[str, str] = {}
    # 2. backend → 出现过的 display_name 集合
    backend_display_names: dict[str, set[str]] = {}

    for cfg in configs:
        dn = cfg.get("display_name")
        if not dn:
            continue
        for k in [cfg.get("name"), cfg.get("model_name"), Path(cfg["__file__"]).stem]:
            if k:
                key_mapping[str(k)] = dn
        b = cfg.get("backend")
        if b:
            backend_display_names.setdefault(b, set()).add(dn)

    # 只有唯一 display_name 的 backend 才做退化映射
    backend_mapping = {
        b: list(dns)[0] for b, dns in backend_display_names.items() if len(dns) == 1
    }

    for r in results:
        if r.get("display_name"):
            continue
        # 优先按精确键
        for key in ("model_name", "name"):
            v = r.get(key)
            if v and str(v) in key_mapping:
                r["display_name"] = key_mapping[str(v)]
                break
        else:
            # 退化到 backend
            b = r.get("backend")
            if b and b in backend_mapping:
                r["display_name"] = backend_mapping[b]
    return results


def _avg_latency_ms(results_for_model: list[dict]) -> float:
    """计算模型在所有退化下的平均延时（ms）

    latency_ms = 1000 / fps，对 fps>0 的组合求平均
    """
    latencies = [1000.0 / r["fps"] for r in results_for_model if r.get("fps", 0) > 0]
    if not latencies:
        return 0.0
    return sum(latencies) / len(latencies)


def print_matrix_table(results: list[dict]) -> None:
    """打印模型 × 退化矩阵对比表 + 平均延时

    Args:
        results: 评估结果列表
    """
    if not results:
        print("(无结果)")
        return

    models = sorted({_row_id(r) for r in results})
    degradations = sorted({r.get("degradation", "clean") for r in results})

    print()
    print("=" * 100)
    print(f"模型 × 退化 矩阵评估（共 {len(results)} 组结果）")
    print("=" * 100)

    # ===== 表 1：acc 矩阵 + 平均延时 =====
    header = "│ model".ljust(20)
    for deg in degradations:
        header += f"│ {deg[:18]:<18}"
    header += f"│ {'avg_latency':<14}│"
    print(header)
    print("┼" + "─" * 19 + ("┼" + "─" * 18) * len(degradations) + "┼" + "─" * 14 + "┼")

    for model in models:
        model_results = [r for r in results if _row_id(r) == model]
        row = f"│ {model[:18]:<18}"
        for deg in degradations:
            match = next(
                (r for r in model_results if r.get("degradation", "clean") == deg),
                None,
            )
            cell = f"{match['acc']*100:.1f}%" if match else "-"
            row += f"│ {cell:<18}"
        avg_lat = _avg_latency_ms(model_results)
        row += f"│ {avg_lat:>6.1f} ms{' '*4}│"
        print(row)

    # ===== 表 2：详细指标（acc / ned / fps / latency） =====
    print()
    print("详细指标（acc / norm_edit_dis / fps / latency）：")
    for r in sorted(results, key=lambda x: (_row_id(x), x.get("degradation", ""))):
        m = _row_id(r)
        d = r.get("degradation", "clean")
        fps = r.get("fps", 0)
        latency = 1000.0 / fps if fps > 0 else 0
        print(
            f"  {m:<18} + {d:<18}: "
            f"acc={r['acc']*100:6.2f}%  ned={r['norm_edit_dis']*100:6.2f}%  "
            f"fps={fps:6.2f}  latency={latency:6.1f} ms"
        )


def load_reports(report_dir: str | Path) -> list[dict]:
    """从 output/reports/ 下加载所有 eval_report.json"""
    report_dir = Path(report_dir)
    if not report_dir.exists():
        return []
    results = []
    for json_path in sorted(report_dir.rglob("eval_report.json")):
        try:
            results.append(json.loads(json_path.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[warn] 无法读取 {json_path}: {e}")
    return results


def save_matrix_report(results: list[dict], out_path: str | Path) -> str:
    """保存矩阵对比的 JSON 报告"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(out_path)

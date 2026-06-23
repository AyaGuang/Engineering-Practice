"""ocr_eval.convert - parquet → PaddleOCR 评估格式

将 HuggingFace 风格的 parquet 数据集（含 image.bytes + text 字段）转换为
PaddleOCR 评估所需的格式：
- 解压图片到 {out_dir}/images/{idx:06d}.jpg
- 生成 {out_dir}/val_list.txt（每行：images/xxx.jpg<TAB>标签）
- 跳过空标签、超长、字典外字符（OOV）

兼容的数据 schema（如本仓库附带的 val-00000-of-00001-*.parquet）：
    required group schema {
      optional group image {
        optional binary bytes;
        optional binary path (String);
      }
      optional binary text (String);
    }
"""
from pathlib import Path

import pyarrow.parquet as pq

from .metrics import norm_edit_dis  # noqa: F401  (re-export 方便外部使用)


def load_dict(dict_path: str | Path | None) -> set[str]:
    """读取 PaddleOCR 字典文件，返回字符集合

    字典格式：每行一个字符（UTF-8）。若路径为 None 或不存在，返回空集合（跳过 OOV 检查）。
    """
    if dict_path is None:
        return set()
    dict_path = Path(dict_path)
    if not dict_path.exists():
        return set()

    chars: set[str] = set()
    with open(dict_path, encoding="utf-8") as f:
        for line in f:
            ch = line.strip()
            if ch:
                chars.add(ch)
    # use_space_char=True 时，空格也是合法字符
    chars.add(" ")
    return chars


def convert_parquet(
    parquet_path: str | Path,
    out_dir: str | Path,
    dict_path: str | Path | None = None,
    limit: int = 0,
    max_text_length: int = 25,
    label_file_name: str = "val_list.txt",
) -> dict:
    """将 parquet 转换为 PaddleOCR 评估格式

    Args:
        parquet_path: parquet 文件路径
        out_dir: 输出目录（图片子目录与 val_list.txt 都在此）
        dict_path: 字典文件（可选，用于 OOV 检查）
        limit: 处理前 N 条（0 = 全量）
        max_text_length: 最大标签长度，超过则跳过
        label_file_name: 输出标注文件名

    Returns:
        统计信息 dict（valid / skipped_empty / skipped_too_long / skipped_oov / ...）
    """
    out_dir = Path(out_dir)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    valid_chars = load_dict(dict_path)

    pf = pq.ParquetFile(parquet_path)
    total = pf.metadata.num_rows
    n_to_process = limit if limit > 0 else total

    label_lines: list[str] = []
    skipped_oov = 0
    skipped_empty = 0
    skipped_too_long = 0
    oov_counter: dict[str, int] = {}

    processed = 0
    for rg_idx in range(pf.metadata.num_row_groups):
        if processed >= n_to_process:
            break
        table = pf.read_row_group(rg_idx)
        image_col = table.column("image")
        text_col = table.column("text")

        for i in range(len(image_col)):
            if processed >= n_to_process:
                break
            img_struct = image_col[i].as_py()
            text = text_col[i].as_py()

            if not text:
                skipped_empty += 1
                continue

            if len(text) > max_text_length:
                skipped_too_long += 1
                continue

            if valid_chars:
                oov_chars = set(text) - valid_chars
                if oov_chars:
                    skipped_oov += 1
                    for c in oov_chars:
                        oov_counter[c] = oov_counter.get(c, 0) + 1
                    continue

            img_bytes = img_struct["bytes"]
            img_name = f"{processed:06d}.jpg"
            (img_dir / img_name).write_bytes(img_bytes)

            label_lines.append(f"images/{img_name}\t{text}")
            processed += 1

    label_path = out_dir / label_file_name
    label_path.write_text("\n".join(label_lines) + "\n", encoding="utf-8")

    return {
        "parquet_path": str(parquet_path),
        "out_dir": str(out_dir),
        "total_in_parquet": total,
        "processed_requested": n_to_process,
        "valid": len(label_lines),
        "skipped_empty": skipped_empty,
        "skipped_too_long": skipped_too_long,
        "skipped_oov": skipped_oov,
        "top_oov_chars": sorted(oov_counter.items(), key=lambda x: -x[1])[:10],
        "label_file": str(label_path),
        "image_dir": str(img_dir),
        "dict_size": len(valid_chars),
    }

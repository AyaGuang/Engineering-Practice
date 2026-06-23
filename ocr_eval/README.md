# OCR 评估工具包

独立、可复用的 OCR 模型评估模块，支持**多模型对比**与**退化鲁棒性评估**。

## 简介

本工具包用于评估 OCR 模型（PaddleOCR、EasyOCR）在自定义数据集上的识别能力，支持：

- 📊 **标准指标**：acc、norm_edit_dis、长度分布、错误样本分析
- 🔀 **多模型对比**：通过 Backend 抽象层，统一接口评估不同 OCR 框架
- 🌫️ **退化鲁棒性**：low_light / shadow / motion_blur / skew_perspective 等真实场景退化
- 📋 **矩阵评估**：一键跑模型 × 退化所有组合，生成对比报告

## 🏆 基线评估结果（1 万条样本）

基于内置的中文文本行数据集（5 万条 HuggingFace parquet 验证集），3 个模型 × 5 种退化 = 15 组合的完整矩阵：

```
======================================================================================
│ model         │ clean   │ low_light │ motion_blur │ shadow  │ skew   │ avg_latency │
├───────────────┼─────────┼───────────┼─────────────┼─────────┼────────┼─────────────┤
│ PaddleOCR v6  │ 91.4%   │  78.7%    │   65.3%     │ 91.1%   │ 90.2%  │  ~25 ms     │
│ PP-OCR-v5     │ 73.3%   │  68.7%    │   50.1%     │ 73.0%   │ 72.1%  │  ~30 ms     │
│ EasyOCR       │ 29.9%   │   9.3%    │    0.2%     │ 29.5%   │ 22.9%  │  ~98 ms     │
======================================================================================
```

### 💡 核心洞察

1. **PaddleOCR v6 全面领先**：clean acc 91.4%，相比 v5 提升 +18 个百分点，且推理速度快 20%+
2. **motion_blur 是通用弱点**：v6 跌至 65.3%、v5 跌至 50.1%、EasyOCR 直接 0.2%
3. **shadow / skew 对 v6 几乎无影响**：保持 90%+ 准确率
4. **中文开源 OCR 生态断层**：EasyOCR 不到 30%，DocTR/Surya 等其他模型不支持中文

详细数据见 [`output/reports/matrix_report.json`](output/reports/matrix_report.json)。

## 目录结构

```
ocr_eval/
├── README.md                         # 本文档
├── requirements.txt                  # 基础依赖
├── ocr_eval/                         # 主 Python 包
│   ├── __init__.py
│   ├── convert.py                    # parquet → PaddleOCR 格式
│   ├── metrics.py                    # 指标计算（与模型无关）
│   ├── evaluate.py                   # 评估主流程（支持 backend + degradation）
│   ├── report.py                     # 控制台 + JSON 报告
│   ├── compare.py                    # 多模型对比汇总
│   ├── visualize.py                  # 退化对比图生成
│   ├── backends/                     # 🎯 模型后端
│   │   ├── base.py                   #    抽象基类
│   │   ├── paddle_ocr.py             #    PaddleOCR 实现（PaddlePaddle）
│   │   ├── trocr.py                  #    TrOCR 实现（PyTorch + HF，中文支持差）
│   │   └── easyocr.py                #    EasyOCR 实现（PyTorch + CRNN）
│   └── degradations/                 # 🌫️ 图像退化
│       ├── base.py                   #    抽象基类
│       ├── low_light.py              #    低光照 + 色温 + 暗角 + 感光噪点
│       ├── shadow.py                 #    随机阴影遮挡
│       ├── motion_blur.py            #    方向性运动模糊
│       └── skew_perspective.py       #    旋转 + 透视
├── scripts/
│   ├── run_convert.py                # 转换 CLI
│   ├── run_evaluate.py               # 单次评估 CLI
│   ├── run_compare.py                # 多模型对比 CLI（clean）
│   ├── run_matrix.py                 # 模型 × 退化矩阵 CLI
│   └── run_missing.py                # 自动检测并补跑缺失组合
├── configs/
│   ├── models/                       # 模型配置（yaml）
│   │   ├── paddleocr_v6_medium.yaml
│   │   ├── paddleocr_v5_server.yaml
│   │   └── easyocr_chinese.yaml
│   └── degradations/                 # 退化参数（yaml）
│       ├── low_light.yaml
│       ├── shadow.yaml
│       ├── motion_blur.yaml
│       └── skew_perspective.yaml
├── data/
│   └── val-*.parquet                 # 原始数据集
└── output/                           # 自动生成（gitignore）
    ├── parquet_val/                  # 转换后的图片 + 标注
    ├── samples/                      # 退化对比图
    └── reports/                      # 评估报告
```

## 环境要求

- Python 3.10+
- PaddlePaddle ≥ 3.0（PaddleOCR backend，推荐 GPU 版）
- PyTorch + easyocr（EasyOCR backend）

### 安装

```bash
# 1. 安装 PaddlePaddle GPU 版（推荐 CUDA 11.8）
python -m pip install paddlepaddle-gpu==3.3.1 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# 2. 安装本工具包基础依赖
pip install -r requirements.txt
```

## 模型配置

本工具包**不含模型文件**，需您自行下载并放置。

### 下载 PaddleOCR 推理模型

从 [PaddleOCR 模型列表](https://paddlepaddle.github.io/PaddleOCR/latest/version3.x/module_usage/text_recognition.html) 下载推理模型（`.tar` 格式），解压后放置到：

```
<你的工作区>/
├── PaddleOCR/                       # PaddleOCR 仓库检出（含推理模型）
│   └── models/
│       ├── PP-OCRv6_medium_rec/      # v6 medium（默认）
│       └── PP-OCRv5_server_rec_infer/# v5 server（版本对比）
└── homework_ocr_grader/             # 本仓库
    └── ocr_eval/                    # 在此目录运行评估脚本
```

默认配置（`configs/models/*.yaml` 里的 `model_dir: ../PaddleOCR/models/...`）即假设 `PaddleOCR/` 与本仓库同级。若你的目录布局不同，编辑对应 yaml 的 `model_dir`，或运行时用 `--model_dir` 覆盖；OOV 字典路径同理用 `--dict` 覆盖（缺失时自动跳过 OOV 检查）。

EasyOCR 首次使用时会**自动下载**模型到 `~/.EasyOCR/model/`，无需手动配置。

## 快速开始

### 1. 转换数据集

```bash
cd homework_ocr_grader/ocr_eval

# 试运行（前 100 条）
python scripts/run_convert.py --demo

# 全量转换（5 万条）
python scripts/run_convert.py
```

### 2. 单模型评估

```bash
# clean（原图）
python scripts/run_evaluate.py --backend paddleocr --limit 1000

# 应用低光照退化
python scripts/run_evaluate.py --backend paddleocr --degradation low_light

# 应用运动模糊 + 保存对比图
python scripts/run_evaluate.py --degradation motion_blur --save_samples 10
```

### 3. 模型 × 退化 矩阵评估

```bash
# 全矩阵（所有配置的模型 × 所有配置的退化）
python scripts/run_matrix.py --limit 10000

# 含对比图
python scripts/run_matrix.py --save_samples 5

# 自动检测并补跑缺失样本数的组合
python scripts/run_missing.py
```

**矩阵报告示例**：

```
======================================================================================
│ model         │ clean   │ low_light │ motion_blur │ shadow  │ skew   │ avg_latency │
├───────────────┼─────────┼───────────┼─────────────┼─────────┼────────┼─────────────┤
│ PaddleOCR     │ 91.4%   │  78.7%    │   65.3%     │ 91.1%   │ 90.2%  │   25 ms     │
│ ...                                                                              
======================================================================================
```

## 评估指标解读

| 指标 | 含义 | 适用场景 |
|---|---|---|
| **acc** | 完全匹配准确率 | 短答案（数字、字母、符号） |
| **norm_edit_dis** | 归一化编辑距离 | 长文本（句子、段落） |
| **fps** | 每秒处理图片数 | 部署吞吐量参考 |
| **avg_latency** | 平均单张延时（ms）= 1000/fps | 用户体验参考 |
| **length_distribution** | 按标签长度的准确率 | 诊断长文本性能 |
| **wrong_samples** | 错误样本（按 ned 升序） | 诊断错误模式 |

## 退化参数说明

所有退化都有合理的默认参数（基于真实场景）：

| 退化 | 参数 | 默认值 | 真实场景 |
|---|---|---|---|
| **low_light** | brightness | 0.5 | 台灯下拍作业 |
| | color_temp_k | 2800 | 暖黄光 |
| | vignette | 0.4 | 桌面光照不均 |
| | noise_std | 8.0 | 高 ISO 感光噪点 |
| **shadow** | n_shadows | 2 | 阴影条数 |
| | shadow_intensity | 0.55 | 阴影最深处的暗度 |
| | width_ratio | 0.15-0.35 | 阴影宽度占图宽比例 |
| | feather | 35 | 羽化半径（柔和边缘） |
| **motion_blur** | kernel_size | 7 | 模糊核大小（约占图高 1/5） |
| | angle_range | 0-360° | 运动方向（全角度随机） |
| **skew_perspective** | max_angle | 5° | 手持拍摄抖动 |
| | perspective | 0.02 | 纸张弯曲 |

参数可通过修改 `configs/degradations/*.yaml` 自定义。

## Backend 开发指南

要添加新的 OCR 模型，只需：

1. **实现 backend**（参考 `ocr_eval/backends/paddle_ocr.py`）
2. **注册**到 `ocr_eval/backends/__init__.py`
3. **添加配置** `configs/models/your_model.yaml`（含 `display_name`）

## 常见问题

### Q: 报错 "Model name mismatch"

PaddleOCR 多版本切换时，需要在 yaml 里指定 `model_name` 字段，与 `inference.yml` 中的 model_name 匹配。

### Q: CPU 推理很慢

安装 GPU 版 paddlepaddle（见「环境要求」）。运行时关闭其他占用 GPU 的程序（如 bilibili、QQ 等），否则 fps 会从 ~50 暴跌到 ~1。

### Q: 后台任务被中断，结果不完整

用 `scripts/run_missing.py` 自动检测并补跑样本数不足的组合：

```bash
python scripts/run_missing.py  # 默认补齐到 10000 条
```

### Q: motion_blur 后 acc 暴跌

这是预期行为——方向性模糊会破坏文字笔画特征。改进方向：
- 训练数据加入运动模糊增强
- 或部署时引导用户保持稳定拍摄

## 许可证

Apache 2.0

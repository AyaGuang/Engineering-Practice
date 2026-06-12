[根目录](../CLAUDE.md) > **backend**

# backend -- 后端服务模块

> AI 上下文文档 -- 自动生成于 2026-06-12T21:10:52+0800

## 模块职责

提供手写作业 OCR 识别与自动批改的 REST API 服务。基于 Flask 框架，整合 PaddleOCR 引擎、图像预处理、文本解析、批改评分和数据持久化功能。运行于 `http://127.0.0.1:5000`。

---

## 入口与启动

- **入口文件**: `app.py` -- Flask 应用定义与所有 API 路由
- **启动方式**: `python app.py`（在 backend 目录下执行）
- **统一启动**: 通过根目录 `launcher.py` 以子进程方式启动

---

## 目录结构

```
backend/
  app.py              -- Flask 应用入口，API 路由定义
  config.py           -- 后端配置（端口、阈值、数据库等）
  database.py         -- SQLAlchemy ORM 模型与数据库操作
  sample_template.json -- 示例答案模板
  homework_grader.db  -- SQLite 数据库文件（运行时生成）
  core/
    __init__.py
    ocr_engine.py     -- PaddleOCR 封装（单例模式）
    preprocessor.py   -- 图像预处理流水线
    parser.py         -- OCR 文本 -> 题号-答案对解析
    grader.py         -- 批改引擎（填空/选择/计算三种题型）
    exporter.py       -- CSV/HTML 报告导出
  models/
    __init__.py        -- 导出 Question, QuestionType, OcrResult, QuestionResult, GradingReport
    question.py        -- Question, QuestionType, OcrResult 数据类
    result.py          -- QuestionResult, GradingReport 数据类
  test_grader.py      -- 批改引擎单元测试
  test_database.py    -- 数据库模块单元测试
  test_parser.py      -- 文本解析单元测试
```

---

## 对外接口 (API)

核心 API 路由均在 `app.py` 中定义：

| 方法 | 路径 | 功能 | 关键参数 |
|------|------|------|----------|
| GET | `/api/health` | 健康检查 | -- |
| POST | `/api/upload` | 上传图片 | multipart file |
| POST | `/api/preprocess/<file_id>` | 图像预处理 | -- |
| POST | `/api/ocr/<file_id>` | OCR 识别 | -- |
| POST | `/api/parse` | OCR 结果解析 | `{ocr_results: [...]}` |
| POST | `/api/grade` | **核心批改** | `{file_id, questions: [{number, type, answer, points}]}` |
| POST | `/api/export/<file_id>` | 导出报告 | `{results, format: "csv"\|"html"}` |
| GET | `/api/history` | 历史查询 | `?keyword=&date_from=&date_to=&min_score=&max_score=&page=&per_page=` |
| GET | `/api/history/<id>` | 批改详情 | -- |
| DELETE | `/api/history/<id>` | 删除记录 | -- |
| GET | `/api/statistics` | 统计概览 | -- |

### 核心批改流水线 (`/api/grade`)

```
接收请求 -> 查找文件 -> OCR识别(ocr_engine.recognize)
    -> 文本解析(parser.parse_answers) -> 逐题批改(grader.grade_all)
    -> 存入数据库 -> 清理临时文件 -> 返回结果
```

---

## 关键依赖与配置

### 内部依赖

| 模块 | 依赖 |
|------|------|
| `app.py` | `config`, `core.*`, `models.question`, `database` |
| `core/ocr_engine.py` | `config`, `models.question.OcrResult`, PaddleOCR |
| `core/preprocessor.py` | OpenCV, numpy |
| `core/parser.py` | `models.question.OcrResult` |
| `core/grader.py` | `config`, `models.question`, `models.result`, fuzzywuzzy |
| `core/exporter.py` | `models.result.GradingReport` |
| `database.py` | `config`, SQLAlchemy |

### 外部依赖

Flask, flask-cors, SQLAlchemy, PaddlePaddle, PaddleOCR, OpenCV, fuzzywuzzy, python-Levenshtein, numpy, Pillow

### 配置项 (`config.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | 5000 | 监听端口 |
| `DEBUG` | True | Flask 调试模式 |
| `UPLOAD_FOLDER` | `backend/uploads/` | 上传文件目录 |
| `MAX_CONTENT_LENGTH` | 16MB | 上传大小限制 |
| `ALLOWED_EXTENSIONS` | png/jpg/jpeg/bmp/tiff/tif | 允许的图片格式 |
| `OCR_LANG` | `ch` | OCR 语言 |
| `OCR_CONFIDENCE_THRESHOLD` | 0.5 | OCR 置信度过滤阈值 |
| `FUZZY_MATCH_THRESHOLD` | 80 | 填空题模糊匹配阈值 |
| `CALCULATION_TOLERANCE` | 0.001 | 计算题数值容差 (0.1%) |
| `PARTIAL_MATCH_THRESHOLD` | 90 | 部分匹配阈值 |
| `DB_NAME` | `homework_grader.db` | SQLite 数据库文件名 |

---

## 数据模型

### 业务数据类 (`models/`)

- **QuestionType** (Enum): `fill_blank` / `multiple_choice` / `calculation`，带 `display_name` 属性
- **Question** (dataclass): 题号、题型、标准答案、分值、备选答案
- **OcrResult** (dataclass): 边界框坐标、识别文本、置信度
- **QuestionResult** (dataclass): 题目、识别文本、是否正确、匹配度、得分
- **GradingReport** (dataclass): 批改结果列表，自动计算 total_points / earned_points / percentage

### ORM 模型 (`database.py`)

- **Homework** (`homeworks` 表): file_id(唯一索引)、原始文件名、存储文件名、上传时间、图片路径
- **GradingRecord** (`grading_records` 表): 关联 Homework、批改时间、总分、得分、得分率、OCR 文本数
- **QuestionResultRecord** (`question_results` 表): 关联 GradingRecord、题号、题型、识别文本、标准答案、是否正确、匹配度、得分

关系：Homework 1:N GradingRecord 1:N QuestionResultRecord（级联删除）

---

## 核心模块说明

### ocr_engine.py

- PaddleOCR 单例封装，使用项目内置模型（`models/PP-OCRv5_server_det/` + `models/PP-OCRv5_server_rec/`）
- `recognize(image)` 返回按位置排序的 `OcrResult` 列表（先按 Y 坐标行分组，行内按 X 排序）
- 使用 PaddleOCR 3.x 的 `predict()` API，数据在 `res` 键下

### preprocessor.py

预处理流水线：`to_grayscale` -> `denoise` (fastNlMeansDenoising) -> `deskew` (Canny + HoughLinesP 旋转校正) -> `binarize` (自适应二值化)

### parser.py

使用正则表达式从 OCR 文本中提取题号和答案。支持五种题号格式：
- `(1)` / `（1）` 括号格式
- `第1题` 格式
- `例1` 格式
- `1.` / `1、` / `1)` 格式
- `1．` 全角句点格式

支持多行答案合并（续行追加到当前题号）。

### grader.py

三种题型批改逻辑：

| 题型 | 方法 | 匹配策略 |
|------|------|----------|
| 填空题 | `grade_fill_blank()` | 文本归一化 -> 精确匹配 -> 备选答案 -> fuzz.ratio 模糊匹配(>=80%) -> fuzz.partial_ratio 部分匹配(>=90%, 乘0.9系数) |
| 选择题 | `grade_multiple_choice()` | 提取A-F字母集合 -> 精确匹配 -> 多选部分分(子集且无错误选项, 50%系数) |
| 计算题 | `grade_calculation()` | 数学符号归一化 -> 等号后提取数值 -> 纯数字解析 -> AST安全表达式求值 -> 数值比较(容差0.1%) |

### exporter.py

- `export_csv()`: UTF-8-BOM 编码 CSV，含题号/题型/识别文字/标准答案/匹配度/得分
- `export_html()`: 带配色的 HTML 报告（正确绿色/错误红色）

---

## 测试与质量

| 测试文件 | 覆盖范围 | 测试用例数 |
|----------|----------|-----------|
| `test_grader.py` | 填空题(精确/空白/备选)、选择题(单选/多选/文本提取)、计算题(数值/表达式/中文符号) | 约15个 |
| `test_database.py` | 作业保存、批改记录 CRUD、历史关键词/日期/分数检索、统计 | 约8个 |
| `test_parser.py` | 多种题号格式、多行合并、空输入 | 约6个 |

运行方式：

```bash
cd backend
python -m unittest test_grader test_database test_parser -v
```

---

## 相关文件清单

| 文件 | 用途 |
|------|------|
| `app.py` | Flask 应用，所有 API 路由 |
| `config.py` | 后端配置常量 |
| `database.py` | ORM 模型与数据库操作 |
| `core/ocr_engine.py` | PaddleOCR 封装 |
| `core/preprocessor.py` | 图像预处理 |
| `core/parser.py` | OCR 文本解析 |
| `core/grader.py` | 批改引擎 |
| `core/exporter.py` | 报告导出 |
| `models/question.py` | Question, QuestionType, OcrResult |
| `models/result.py` | QuestionResult, GradingReport |
| `sample_template.json` | 示例答案模板 |
| `test_grader.py` | 批改引擎测试 |
| `test_database.py` | 数据库测试 |
| `test_parser.py` | 解析模块测试 |

---

## 变更记录 (Changelog)

| 时间 | 操作 |
|------|------|
| 2026-06-12T21:10:52+0800 | 初始化模块文档 |

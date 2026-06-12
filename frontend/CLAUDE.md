[根目录](../CLAUDE.md) > **frontend**

# frontend -- 前端 GUI 模块

> AI 上下文文档 -- 自动生成于 2026-06-12T21:10:52+0800

## 模块职责

基于 PyQt5 的桌面 GUI 客户端。提供作业图片预览、标准答案编辑、批改结果展示、历史记录查询等交互界面。通过 `api_client.py` 以 HTTP 请求调用后端 Flask API，自身不包含业务逻辑。

---

## 入口与启动

- **入口文件**: `main.py` -- 创建 QApplication，加载样式表，启动主窗口
- **启动方式**: `python main.py`（在 frontend 目录下执行）
- **统一启动**: 通过根目录 `launcher.py` 启动

---

## 目录结构

```
frontend/
  __init__.py          -- 空包标记
  main.py              -- PyQt5 应用入口
  config.py            -- 前端配置（API 地址、文件过滤器）
  api_client.py        -- 后端 API HTTP 客户端封装
  ui/
    __init__.py         -- 空包标记
    main_window.py      -- 主窗口（QMainWindow），集成所有面板
    image_panel.py      -- 图片预览面板（原图/处理后/OCR文字切换）
    answer_panel.py     -- 标准答案编辑面板（表格 + 模板保存/加载）
    result_panel.py     -- 批改结果展示面板（带颜色标记的表格）
    history_panel.py    -- 历史记录面板（搜索/分页/详情/删除）
    resources/
      style.qss         -- 全局 QSS 样式表
```

---

## 对外接口

本模块为 GUI 客户端，不暴露编程接口。与后端的所有通信通过 `ApiClient` 类完成。

### ApiClient 方法一览 (`api_client.py`)

| 方法 | 对应后端 API | 说明 |
|------|-------------|------|
| `health_check()` | GET `/api/health` | 检查后端可用性 |
| `upload_image(path)` | POST `/api/upload` | 上传图片文件 |
| `preprocess(file_id)` | POST `/api/preprocess/<id>` | 请求图像预处理 |
| `ocr_recognize(file_id)` | POST `/api/ocr/<id>` | 请求 OCR 识别 |
| `grade(file_id, questions)` | POST `/api/grade` | 核心：一步完成 OCR + 批改 |
| `export_report(file_id, results, fmt)` | POST `/api/export/<id>` | 导出 CSV/HTML 报告 |
| `get_history(**params)` | GET `/api/history` | 查询历史记录 |
| `get_history_detail(id)` | GET `/api/history/<id>` | 获取批改详情 |
| `delete_history(id)` | DELETE `/api/history/<id>` | 删除批改记录 |
| `get_statistics()` | GET `/api/statistics` | 获取统计数据 |

---

## 关键依赖与配置

### 内部依赖

| 文件 | 依赖 |
|------|------|
| `main.py` | `ui.main_window.MainWindow`, `config` |
| `main_window.py` | `config`, `ui.image_panel`, `ui.answer_panel`, `ui.result_panel`, `ui.history_panel`, `api_client.ApiClient` |
| `image_panel.py` | OpenCV (numpy 转 QPixmap), PyQt5 |
| `answer_panel.py` | `config`, PyQt5 |
| `result_panel.py` | PyQt5 |
| `history_panel.py` | `api_client.ApiClient`, PyQt5 |
| `api_client.py` | `config`, requests |

### 外部依赖

PyQt5 (>=5.15.0), requests (>=2.31.0), OpenCV (图片显示)

### 配置项 (`config.py`)

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `API_BASE_URL` | `http://127.0.0.1:5000` | 后端 API 地址 |
| `IMAGE_FILTER` | 图片文件过滤器 | 文件对话框用 |
| `TEMPLATE_FILTER` | JSON 文件过滤器 | 模板文件对话框用 |
| `CSV_FILTER` | CSV 文件过滤器 | 导出对话框用 |
| `HTML_FILTER` | HTML 文件过滤器 | 导出对话框用 |

---

## UI 面板说明

### MainWindow (`main_window.py`)

- 主窗口包含两个 Tab：**"作业批改"** 和 **"历史记录"**
- 批改页面布局：左侧 ImagePanel | 右侧上方 AnswerPanel + 右侧下方 ResultPanel
- 工具栏：打开图片(Ctrl+O)、开始批改(Ctrl+G)、导出CSV、导出HTML、历史记录(Ctrl+H)
- `GradeWorker` (QThread)：在子线程中调用 API，避免阻塞 UI

### ImagePanel (`image_panel.py`)

- 显示作业图片（原图/处理后切换）
- 支持切换显示 OCR 识别文字（带置信度）
- numpy 数组转 QPixmap 显示，自适应面板宽度

### AnswerPanel (`answer_panel.py`)

- QTableWidget 表格编辑标准答案（题号/题型/标准答案/分值）
- 题型下拉选择：填空题/选择题/计算题
- 支持保存/加载 JSON 格式的答案模板
- `QuestionData` dataclass 作为前端轻量级题目数据结构

### ResultPanel (`result_panel.py`)

- 以表格展示批改结果（题号/题型/识别文字/标准答案/匹配度/得分）
- 正确绿色 / 错误红色 行背景色
- 底部显示总分汇总

### HistoryPanel (`history_panel.py`)

- 搜索条件：文件名关键词、日期范围、得分率范围
- 分页浏览历史记录（默认每页15条）
- 双击/查看详情弹出 DetailDialog
- 支持删除记录
- 底部显示统计数据（总作业数/总批改数/平均得分率）
- 列表行颜色：>=80% 绿色、60%-80% 黄色、<60% 红色

### 样式 (`resources/style.qss`)

全局 QSS 样式，定义了面板标题、工具栏(#4a90d9 蓝色主题)、表格、按钮、状态栏等样式。

---

## 数据模型（前端本地）

### QuestionData (`answer_panel.py`)

```python
@dataclass
class QuestionData:
    number: int
    q_type: str         # 'fill_blank' | 'multiple_choice' | 'calculation'
    standard_answer: str
    points: float = 1.0
```

前端使用 `QuestionData` 而非后端的 `Question` 类，保持前后端解耦。

---

## 测试与质量

前端 GUI 模块目前没有自动化测试。建议的测试方向：
- `api_client.py` 可使用 `unittest.mock` 模拟 requests 进行单元测试
- GUI 面板可使用 `QTest` 进行自动化 UI 测试

---

## 相关文件清单

| 文件 | 用途 |
|------|------|
| `main.py` | PyQt5 应用入口 |
| `config.py` | 前端配置 |
| `api_client.py` | 后端 API 客户端 |
| `ui/main_window.py` | 主窗口与 GradeWorker 线程 |
| `ui/image_panel.py` | 图片预览面板 |
| `ui/answer_panel.py` | 标准答案编辑面板 |
| `ui/result_panel.py` | 批改结果展示面板 |
| `ui/history_panel.py` | 历史记录面板 |
| `ui/resources/style.qss` | 全局样式表 |

---

## 变更记录 (Changelog)

| 时间 | 操作 |
|------|------|
| 2026-06-12T21:10:52+0800 | 初始化模块文档 |

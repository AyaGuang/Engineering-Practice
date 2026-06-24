"""
* 前端配置 - 后端 API 地址与各类文件对话框过滤器
* 被 api_client / 各 UI 面板通过 import config 引用
* create by 林嘉晨
* copyright USTC
* 2026.03.13
"""

# 后端API地址
API_BASE_URL = 'http://127.0.0.1:5000'

# 支持的图片格式过滤
IMAGE_FILTER = "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;所有文件 (*)"

# 答案模板文件过滤
TEMPLATE_FILTER = "JSON文件 (*.json);;所有文件 (*)"

# 导出文件过滤
CSV_FILTER = "CSV文件 (*.csv);;所有文件 (*)"
HTML_FILTER = "HTML文件 (*.html);;所有文件 (*)"

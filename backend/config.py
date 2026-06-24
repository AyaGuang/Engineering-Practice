"""
* 后端配置 - 服务端口、上传限制、OCR 与批改阈值、数据库名等常量
* 被 app.py / core / database 等模块通过 import config 引用
* create by 廖帅
* copyright USTC
* 2026.03.13
"""
import os

# 服务器配置
HOST = '127.0.0.1'
PORT = 5000
# 关闭debug的reloader：运行中文件变动会导致服务重启，中断正在进行的批改请求
DEBUG = False

# 上传文件配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}

# OCR配置
OCR_LANG = 'ch'
OCR_CONFIDENCE_THRESHOLD = 0.5

# 批改配置
FUZZY_MATCH_THRESHOLD = 80
CALCULATION_TOLERANCE = 0.001
PARTIAL_MATCH_THRESHOLD = 90

# 数据库配置
DB_NAME = 'homework_grader.db'

# LLM纠错配置（OCR结果纠正）
LLM_API_KEY = os.environ.get('OPENAI_API_KEY', '')
LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-v4-flash')
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com')  # 可选，支持兼容API
LLM_CORRECTION_ENABLED = False  # 默认关闭，由前端请求控制
LLM_TIMEOUT = 30  # 秒

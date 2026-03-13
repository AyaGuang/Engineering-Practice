"""后端配置"""
import os

# 服务器配置
HOST = '127.0.0.1'
PORT = 5000
DEBUG = True

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

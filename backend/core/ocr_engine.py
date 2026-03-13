"""
* QuestionResultRecord class
* PaddleOCR封装模块
* create by 廖帅
* copyright USTC
* 2026.02.23
"""
import os
from typing import List, Union
import numpy as np

from paddleocr import PaddleOCR

import config
from models.question import OcrResult

# 项目内置模型目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, 'models')
_DET_MODEL_DIR = os.path.join(_MODELS_DIR, 'PP-OCRv5_server_det')
_REC_MODEL_DIR = os.path.join(_MODELS_DIR, 'PP-OCRv5_server_rec')

# 全局OCR实例（延迟初始化）
_ocr_instance = None


def get_ocr() -> PaddleOCR:
    """获取或创建OCR实例（单例）"""
    global _ocr_instance
    if _ocr_instance is None:
        import logging
        logging.getLogger('ppocr').setLevel(logging.WARNING)
        _ocr_instance = PaddleOCR(
            lang=config.OCR_LANG,
            text_detection_model_dir=_DET_MODEL_DIR,
            text_recognition_model_dir=_REC_MODEL_DIR,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
    return _ocr_instance


def recognize(image: Union[str, np.ndarray]) -> List[OcrResult]:
    """
    识别图像中的文字。
    参数: 图片路径或numpy数组
    返回: 按位置排序的OcrResult列表
    """
    ocr = get_ocr()
    result = ocr.predict(image)

    ocr_results = []
    for res in result:
        json_data = res.json
        if not json_data:
            continue

        # PaddleOCR 3.x 数据嵌套在 'res' 键下
        data = json_data.get('res', json_data)

        texts = data.get('rec_texts', [])
        scores = data.get('rec_scores', [])
        polys = data.get('rec_polys', [])

        for text, score, poly in zip(texts, scores, polys):
            if score < config.OCR_CONFIDENCE_THRESHOLD:
                continue

            # rec_polys 已经是 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] 格式
            bbox = [[int(p[0]), int(p[1])] for p in poly]

            ocr_results.append(OcrResult(bbox=bbox, text=text, confidence=score))

    # 按位置排序：先按y坐标（上到下），同行按x坐标（左到右）
    ocr_results.sort(key=lambda r: (r.bbox[0][1] // 30, r.bbox[0][0]))

    return ocr_results

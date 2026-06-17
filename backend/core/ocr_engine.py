"""
* OcrEngine class
* PaddleOCR封装模块（PP-OCRv6）
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
_DET_MODEL_DIR = os.path.join(_MODELS_DIR, 'PP-OCRv6_medium_det')
_REC_MODEL_DIR = os.path.join(_MODELS_DIR, 'PP-OCRv6_medium_rec')

# 全局OCR实例（延迟初始化）
_ocr_instance = None


def _build_ocr_kwargs() -> dict:
    """构造PaddleOCR参数。本地模型存在则指定路径，否则交给PaddleOCR自动下载。"""
    kwargs = {
        'lang': config.OCR_LANG,
        'use_doc_orientation_classify': False,
        'use_doc_unwarping': False,
        'use_textline_orientation': False,
        'enable_mkldnn': False,
    }
    det_available = os.path.isdir(_DET_MODEL_DIR)
    rec_available = os.path.isdir(_REC_MODEL_DIR)
    if det_available and rec_available:
        # 优先使用本地模型（离线/已下载场景）
        kwargs['text_detection_model_dir'] = _DET_MODEL_DIR
        kwargs['text_recognition_model_dir'] = _REC_MODEL_DIR
    else:
        # 本地缺失时由PaddleOCR按默认行为自动拉取PP-OCRv6
        # 注意：v6档位为 tiny/small/medium（非v4/v5的mobile/server）
        kwargs['text_detection_model_name'] = 'PP-OCRv6_medium_det'
        kwargs['text_recognition_model_name'] = 'PP-OCRv6_medium_rec'
    return kwargs


def get_ocr() -> PaddleOCR:
    """获取或创建OCR实例（单例）"""
    global _ocr_instance
    if _ocr_instance is None:
        import logging
        import paddle
        logging.getLogger('ppocr').setLevel(logging.WARNING)
        # 禁用oneDNN：PaddlePaddle 3.x的PIR图与oneDNN存在兼容性问题，
        # 会触发"ConvertPirAttribute2RuntimeAttribute not support"异常。
        paddle.set_flags({'FLAGS_use_mkldnn': False})
        _ocr_instance = PaddleOCR(**_build_ocr_kwargs())
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

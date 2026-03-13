"""
* QuestionResultRecord class
* 图像预处理模块 - 灰度、降噪、纠偏、二值化
* create by 林睿埼
* copyright USTC
* 2026.02.05
"""
import cv2
import numpy as np


def preprocess(image_path: str) -> np.ndarray:
    """完整预处理流水线，返回处理后的图像"""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")

    gray = to_grayscale(img)
    denoised = denoise(gray)
    deskewed = deskew(denoised)
    binary = binarize(deskewed)
    return binary


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """转灰度图"""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def denoise(gray: np.ndarray) -> np.ndarray:
    """降噪"""
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def deskew(gray: np.ndarray) -> np.ndarray:
    """倾斜校正"""
    # 边缘检测
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    # Hough线检测
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                            minLineLength=100, maxLineGap=10)
    if lines is None:
        return gray

    # 计算所有线段角度的中位数
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 45:  # 只取近水平线
            angles.append(angle)

    if not angles:
        return gray

    median_angle = np.median(angles)
    if abs(median_angle) < 0.5:  # 角度很小就不校正
        return gray

    # 旋转校正
    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def binarize(gray: np.ndarray) -> np.ndarray:
    """自适应二值化"""
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 11, 2)

"""
线稿生成模块
基于 OpenCV 把彩色图转为适合涂鸦的线稿图

提供两种风格：
- cartoon：卡通涂色书风格，线条清晰封闭，适合小孩涂色
- sketch：铅笔素描风格，线条柔和，更艺术化
"""
import cv2
import numpy as np

from config import Config


def _resize_if_needed(img: np.ndarray, max_size: int = None) -> np.ndarray:
    """若图片过大则等比缩放，避免处理过慢"""
    max_size = max_size or Config.LINEART_MAX_SIZE
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest > max_size:
        scale = max_size / longest
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img


def _decode_image(image_bytes: bytes) -> np.ndarray:
    """把字节流解码成 OpenCV 图像（BGR）"""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解析图片格式，请确认是 JPG / PNG 等常见图像格式")
    return img


def _encode_png(img: np.ndarray) -> bytes:
    """把图像编码为 PNG 字节流"""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("PNG 编码失败")
    return buffer.tobytes()


def _cartoon_lineart(img: np.ndarray) -> np.ndarray:
    """
    卡通涂色书风格：
    1. 双边滤波多次，把色块平滑得更"卡通"，减少琐碎细节
    2. 灰度 + 中值滤波，进一步去噪
    3. 自适应阈值边缘检测，得到清晰封闭轮廓
    4. 形态学闭运算，连接小断点
    """
    # 双边滤波，保留边缘、平滑色块
    smooth = img
    for _ in range(2):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)

    gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    # 自适应阈值 —— 在不同亮度区域使用不同阈值，得到一致的线条
    edges = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=9,
        C=7,
    )

    # 小幅度闭运算填补线条断点
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    return edges


def _sketch_lineart(img: np.ndarray) -> np.ndarray:
    """
    铅笔素描风格：
    经典 "灰度反相 + 模糊 + 颜色减淡(dodge)" 技巧
    生成的图保留更多细腻明暗层次
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), sigmaX=0, sigmaY=0)
    inverted_blurred = 255 - blurred
    # 颜色减淡（color dodge）：base / (255 - blend) * 255
    sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
    return sketch


def generate_lineart(image_bytes: bytes, style: str = "cartoon") -> bytes:
    """
    主入口：把图片字节流转为线稿 PNG 字节流

    参数:
        image_bytes: 原图二进制数据
        style: cartoon（涂色书风格）或 sketch（素描风格）

    返回:
        线稿 PNG 二进制数据
    """
    img = _decode_image(image_bytes)
    img = _resize_if_needed(img)

    style = (style or "cartoon").lower()
    if style == "sketch":
        result = _sketch_lineart(img)
    else:
        # 默认 cartoon
        result = _cartoon_lineart(img)

    return _encode_png(result)


# 暴露给前端使用的风格列表 —— 加新风格时同步更新
AVAILABLE_STYLES = [
    {"value": "cartoon", "label": "涂色书（线条清晰）"},
    {"value": "sketch", "label": "铅笔素描（柔和）"},
]

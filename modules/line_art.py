"""
Line art generation module
Uses OpenCV to convert a color image into a coloring-page-style line drawing.

Two styles:
- cartoon: clean closed lines, ideal for kids to color in
- sketch: pencil sketch style, softer with more tonal variation
"""
import cv2
import numpy as np

from config import Config


def _resize_if_needed(img: np.ndarray, max_size: int = None) -> np.ndarray:
    """Downscale large images to keep processing fast."""
    max_size = max_size or Config.LINEART_MAX_SIZE
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest > max_size:
        scale = max_size / longest
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img


def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode raw bytes into an OpenCV BGR image."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Make sure it is a valid JPG/PNG file.")
    return img


def _encode_png(img: np.ndarray) -> bytes:
    """Encode an image to PNG bytes."""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("Failed to encode PNG output")
    return buffer.tobytes()


def _cartoon_lineart(img: np.ndarray) -> np.ndarray:
    """
    Coloring book style:
    1. Bilateral filter (multiple passes) smooths colors to a more "cartoon" look
    2. Grayscale + median blur further reduces noise
    3. Adaptive threshold gives clean closed contours
    4. Morphological close fills small gaps in the lines
    """
    smooth = img
    for _ in range(2):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)

    gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    # Adaptive threshold — uses different thresholds across regions for consistent lines
    edges = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=9,
        C=7,
    )

    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    return edges


def _sketch_lineart(img: np.ndarray) -> np.ndarray:
    """
    Pencil sketch style:
    Classic "grayscale + invert + blur + color dodge" technique.
    Produces a softer result with more tonal gradient.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), sigmaX=0, sigmaY=0)
    inverted_blurred = 255 - blurred
    # Color dodge: base / (255 - blend) * 255
    sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
    return sketch


def generate_lineart(image_bytes: bytes, style: str = "cartoon") -> bytes:
    """
    Main entry point: convert image bytes to line art PNG bytes.

    Args:
        image_bytes: original image data
        style: "cartoon" (coloring book) or "sketch" (pencil sketch)

    Returns:
        PNG bytes of the line art
    """
    img = _decode_image(image_bytes)
    img = _resize_if_needed(img)

    style = (style or "cartoon").lower()
    if style == "sketch":
        result = _sketch_lineart(img)
    else:
        result = _cartoon_lineart(img)

    return _encode_png(result)


# Available styles for the frontend — keep in sync when adding new styles
AVAILABLE_STYLES = [
    {"value": "cartoon", "label": "Coloring Book (clean lines)"},
    {"value": "sketch", "label": "Pencil Sketch (soft)"},
]

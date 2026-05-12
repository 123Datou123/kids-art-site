"""
Line art generation module
Uses OpenCV to convert a color image into a coloring-page-style line drawing.

Two styles:
- cartoon: clean closed lines, ideal for kids to color in
- sketch: pencil sketch style, softer with more tonal variation

Both styles can output:
- White background (default, for printing)
- Transparent background (for the in-browser coloring tool)
"""
import cv2
import numpy as np

from config import Config


def _resize_if_needed(img: np.ndarray, max_size: int = None) -> np.ndarray:
    """Downscale large images to keep processing fast — but keep more detail than before."""
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
    Coloring book style — IMPROVED VERSION.

    Improvements over v1:
    1. More bilateral filter passes (3 instead of 2) → cleaner regions
    2. Larger kernel + Gaussian adaptive threshold → smoother, more connected lines
    3. Morphology close + erode → lines slightly thicker and gaps filled
    4. Result is much more "coloring book" looking
    """
    # Step 1: Heavy bilateral smoothing — preserves edges, flattens color regions
    smooth = img
    for _ in range(3):
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=80, sigmaSpace=80)

    # Step 2: To grayscale + median blur for noise removal
    gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    # Step 3: Gaussian-weighted adaptive threshold — gives smoother lines than mean version
    edges = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,   # Larger block → smoother regions, fewer broken bits
        C=7,
    )

    # Step 4: Close small gaps in lines
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Step 5: Make lines slightly thicker (erode white → expand black)
    # This makes them more visible and easier for kids to stay inside while coloring
    edges = cv2.erode(edges, kernel, iterations=1)

    return edges


def _sketch_lineart(img: np.ndarray) -> np.ndarray:
    """
    Pencil sketch style — classic dodge technique.
    Softer, more artistic feel with tonal gradients.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inverted = 255 - gray
    blurred = cv2.GaussianBlur(inverted, (21, 21), sigmaX=0, sigmaY=0)
    inverted_blurred = 255 - blurred
    sketch = cv2.divide(gray, inverted_blurred, scale=256.0)
    return sketch


def _to_transparent_rgba(img_gray: np.ndarray) -> np.ndarray:
    """
    Convert a grayscale line art (black lines on white background)
    into an RGBA image with a transparent background.

    Where the source is dark → opaque black.
    Where the source is light → fully transparent.
    Mid-tones get partial transparency for smooth edges.
    """
    h, w = img_gray.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    # Alpha = how dark the pixel is (inverted grayscale)
    alpha = 255 - img_gray
    rgba[:, :, 3] = alpha
    # RGB stays at 0 (black); transparency is controlled by alpha alone
    return rgba


def generate_lineart(image_bytes: bytes, style: str = "cartoon",
                     transparent: bool = False) -> bytes:
    """
    Main entry: convert image bytes to line art PNG bytes.

    Args:
        image_bytes: raw input image
        style: "cartoon" (default, coloring book) or "sketch" (pencil)
        transparent: if True, output PNG has transparent background
                     instead of white (for in-browser coloring overlay)

    Returns:
        PNG bytes
    """
    img = _decode_image(image_bytes)
    img = _resize_if_needed(img)

    style = (style or "cartoon").lower()
    if style == "sketch":
        result = _sketch_lineart(img)
    else:
        result = _cartoon_lineart(img)

    if transparent:
        result = _to_transparent_rgba(result)

    return _encode_png(result)


AVAILABLE_STYLES = [
    {"value": "cartoon", "label": "Coloring Book (clean lines)"},
    {"value": "sketch", "label": "Pencil Sketch (soft)"},
]

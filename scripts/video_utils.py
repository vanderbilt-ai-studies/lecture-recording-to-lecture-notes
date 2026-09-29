#!/usr/bin/env python3
"""Shared helpers for the screen-grab scripts: opening video, masking the
camera thumbnail, and comparing frames."""

import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("opencv-python not found. Installing...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "-q"])
    import cv2
    import numpy as np

FILL_MODES = ("auto", "gray", "black", "none")
GRAY = (128, 128, 128)


def open_video(path: str):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Error: Could not open video {path}", file=sys.stderr)
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, fps, frames / fps, width, height


def read_at(cap, seconds: float):
    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000.0)
    ok, frame = cap.read()
    return frame if ok else None


def parse_mask(value: str | None):
    """Parse 'x,y,w,h' (pixels) into a tuple; 'none' or empty means no mask."""
    if not value or value.lower() == "none":
        return None
    parts = [int(round(float(p))) for p in value.split(",")]
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise ValueError(f"--mask must be x,y,w,h in pixels, got {value!r}")
    return tuple(parts)


def apply_mask(frame, mask, fill: str = "auto"):
    """Paint over the camera thumbnail so it doesn't appear in the screen grab.

    'auto' fills with the median color of a thin ring just outside the box, so
    the box blends into the surrounding background (white page -> white).
    """
    if mask is None or fill == "none":
        return frame
    h_img, w_img = frame.shape[:2]
    x, y, w, h = mask
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w_img, x + w), min(h_img, y + h)
    if x1 <= x0 or y1 <= y0:
        return frame
    out = frame.copy()
    if fill == "gray":
        color = GRAY
    elif fill == "black":
        color = (0, 0, 0)
    else:
        ring = max(4, min(w_img, h_img) // 100)
        rx0, ry0 = max(0, x0 - ring), max(0, y0 - ring)
        rx1, ry1 = min(w_img, x1 + ring), min(h_img, y1 + ring)
        region = frame[ry0:ry1, rx0:rx1].reshape(-1, 3)
        inside = np.zeros((ry1 - ry0, rx1 - rx0), dtype=bool)
        inside[y0 - ry0:y1 - ry0, x0 - rx0:x1 - rx0] = True
        samples = region[~inside.reshape(-1)]
        color = tuple(int(c) for c in np.median(samples, axis=0)) if len(samples) else GRAY
    cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), color, thickness=-1)
    return out


def small_gray(frame, width: int = 320):
    """Downscaled, blurred grayscale copy used for cheap frame comparisons."""
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (width, max(1, round(h * width / w))), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (3, 3), 0)


def changed_fraction(a, b, threshold: int = 20) -> float:
    """Fraction of pixels that differ noticeably between two small_gray images."""
    if a.shape != b.shape:
        b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.count_nonzero(cv2.absdiff(a, b) > threshold)) / a.size


def hhmmss(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def grab_filename(output_dir: str, seconds: float) -> str:
    return os.path.join(output_dir, f"auto_{hhmmss(seconds)}.png")

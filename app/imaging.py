"""Image -> normalized heightmap conversion."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps


def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def image_to_heightmap(
    img: Image.Image,
    cols: int,
    rows: int,
    invert: bool,
    brightness: float,
    contrast: float,
    gamma: float,
) -> np.ndarray:
    """Resample `img` onto a (rows, cols) grid and return a float32 array
    in [0, 1] where 1.0 is the brightest pixel (before invert).

    brightness: -100..100 additive, contrast: -100..100 multiplicative
    around mid-gray, gamma: exponent applied after brightness/contrast.
    """
    gray = img.convert("L").resize((cols, rows), Image.LANCZOS)
    arr = np.asarray(gray, dtype=np.float32) / 255.0

    if brightness:
        arr = arr + (brightness / 100.0)

    if contrast:
        factor = (259 * (contrast + 100)) / (100 * (259 - contrast)) if contrast > -100 else 0.01
        arr = factor * (arr - 0.5) + 0.5

    arr = np.clip(arr, 0.0, 1.0)

    g = max(0.05, float(gamma))
    if g != 1.0:
        arr = np.power(arr, g)

    if invert:
        arr = 1.0 - arr

    return arr.astype(np.float32)


def target_grid_size(
    width_mm: float, height_mm: float, points_per_mm: float, max_points: int = 450
) -> tuple[int, int]:
    """Compute (cols, rows) for a given physical size and desired point
    density, capped so meshes/booleans stay fast."""
    cols = max(8, round(width_mm * points_per_mm))
    rows = max(8, round(height_mm * points_per_mm))
    longest = max(cols, rows)
    if longest > max_points:
        scale = max_points / longest
        cols = max(8, round(cols * scale))
        rows = max(8, round(rows * scale))
    return cols, rows

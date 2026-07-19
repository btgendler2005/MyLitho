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


def _capped_display_size(width_mm: float, height_mm: float, max_px: int) -> tuple[int, int]:
    aspect = width_mm / height_mm
    if aspect >= 1:
        w, h = max_px, round(max_px / aspect)
    else:
        w, h = round(max_px * aspect), max_px
    return max(8, w), max(8, h)


def build_backlight_texture(
    img: Image.Image,
    width_mm: float,
    height_mm: float,
    border_mm: float,
    invert: bool,
    brightness: float,
    contrast: float,
    gamma: float,
    max_px: int = 900,
) -> bytes:
    """Render a display-resolution grayscale PNG approximating backlit
    brightness, independent of the mesh's point count.

    The live 3D preview's mesh resolution is capped for browser
    performance, and coloring the mesh per-vertex would blur the backlit
    preview across each (large, sparse) triangle. Rendering this as a
    separate higher-resolution texture -- sampled per-pixel by the GPU
    instead of interpolated per-vertex -- keeps the backlit preview sharp
    regardless of the print mesh's resolution.
    """
    cols, rows = _capped_display_size(width_mm, height_mm, max_px)
    heightmap = image_to_heightmap(img, cols, rows, invert, brightness, contrast, gamma)
    heightmap, _, _ = apply_border(heightmap, width_mm, height_mm, border_mm)

    # Same falloff curve the old per-vertex approach used: transmitted
    # light through plastic drops off faster than linearly with thickness.
    brightness_curve = np.power(np.clip(heightmap, 0.0, 1.0), 1.6)
    pixels = (brightness_curve * 255).astype(np.uint8)

    out_img = Image.fromarray(pixels, mode="L")
    buf = io.BytesIO()
    out_img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def apply_border(
    heightmap: np.ndarray, width_mm: float, height_mm: float, border_mm: float
) -> tuple[np.ndarray, float, float]:
    """Pad a heightmap with a flat, fully-dark border ring.

    A pixel value of 0.0 maps (via shapes.thickness_grid) to max thickness,
    so the padded border comes out as a solid, uniform-height mat around
    the image -- reusing the existing thickness formula rather than
    threading a separate "border thickness" concept through the mesh code.
    """
    if border_mm <= 0:
        return heightmap, width_mm, height_mm

    rows, cols = heightmap.shape
    border_px_x = max(1, round(border_mm * (cols / width_mm)))
    border_px_y = max(1, round(border_mm * (rows / height_mm)))

    padded = np.pad(
        heightmap,
        ((border_px_y, border_px_y), (border_px_x, border_px_x)),
        mode="constant",
        constant_values=0.0,
    )
    new_width_mm = width_mm + 2 * border_mm
    new_height_mm = height_mm + 2 * border_mm
    return padded, new_width_mm, new_height_mm

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


def crop_to_frame(
    img: Image.Image,
    width_mm: float,
    height_mm: float,
    scale: float,
    center_x: float,
    center_y: float,
) -> Image.Image:
    """Extract the sub-rectangle of `img` that will fill the panel.

    scale=1.0 picks the largest rectangle matching the panel's aspect
    ratio that fits inside the source photo (a "cover" fit -- uses as
    much of the source as possible with no distortion or empty space).
    scale>1 shrinks that rectangle around (center_x, center_y) -- given
    as fractions of the source image's width/height -- to zoom in.
    Clamped so the crop window never leaves the source image bounds.
    """
    target_aspect = width_mm / height_mm
    src_w, src_h = img.size
    src_aspect = src_w / src_h

    if src_aspect > target_aspect:
        base_h = float(src_h)
        base_w = src_h * target_aspect
    else:
        base_w = float(src_w)
        base_h = src_w / target_aspect

    scale = max(1.0, scale)
    crop_w = base_w / scale
    crop_h = base_h / scale

    cx = min(max(center_x, 0.0), 1.0) * src_w
    cy = min(max(center_y, 0.0), 1.0) * src_h

    x0 = min(max(cx - crop_w / 2, 0.0), src_w - crop_w)
    y0 = min(max(cy - crop_h / 2, 0.0), src_h - crop_h)

    return img.crop((round(x0), round(y0), round(x0 + crop_w), round(y0 + crop_h)))


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


def apply_inset_border(img: Image.Image, size_mm: float, border_mm: float) -> Image.Image:
    """Shrinks `img` and centers it on a black canvas of the same pixel
    size, leaving a border_mm-wide margin -- once converted to a
    heightmap, black maps to max thickness (see apply_border), giving
    the same flat picture-frame-mat look, but WITHOUT changing the
    image's own physical size the way apply_border does. Cube panels
    must stay exactly size_mm x size_mm on every edge since the whole
    frame (post spacing, groove/pocket placement) is derived from that
    one number -- growing the panel to fit a border, like the
    single-photo flow does, would grow it right out of its own frame.
    """
    if border_mm <= 0:
        return img
    w, h = img.size
    inset_x = round(w * border_mm / size_mm)
    inset_y = round(h * border_mm / size_mm)
    inner_w = max(1, w - 2 * inset_x)
    inner_h = max(1, h - 2 * inset_y)
    resized = img.resize((inner_w, inner_h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), (0, 0, 0))
    canvas.paste(resized, (inset_x, inset_y))
    return canvas


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

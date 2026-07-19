"""Top-level orchestration: image + params -> heightmap / mesh(es)."""

from __future__ import annotations

import base64

import trimesh

from . import accessories, geometry, imaging, shapes
from .models import LithophaneParams

# Preview resolution tracks the user's Detail slider (like the final
# export does) so cranking Detail sharpens the live view too. Preview never
# does server-side booleans (novelty shapes are masked cheaply in JS), so
# this can go nearly as high as the boolean-free final export cap without
# a performance hit -- the goal is for preview and final STL to match at
# typical panel sizes/detail settings, not just be "close."
PREVIEW_MAX_POINTS = 550

# Booleans (novelty shape clipping) get noticeably slower with resolution,
# so cap those exports lower than the boolean-free flat/curved path.
FINAL_MAX_POINTS_SIMPLE = 700
FINAL_MAX_POINTS_BOOLEAN = 380


def _bordered_dims(params: LithophaneParams) -> tuple[float, float]:
    return params.width_mm + 2 * params.border_mm, params.height_mm + 2 * params.border_mm


def build_preview_heightmap(image_bytes: bytes, params: LithophaneParams) -> dict:
    img = imaging.load_image(image_bytes)
    cols, rows = imaging.target_grid_size(
        params.width_mm, params.height_mm, points_per_mm=params.detail, max_points=PREVIEW_MAX_POINTS
    )
    heightmap = imaging.image_to_heightmap(
        img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma
    )
    heightmap, width_mm, height_mm = imaging.apply_border(heightmap, params.width_mm, params.height_mm, params.border_mm)
    rows, cols = heightmap.shape

    texture_png = imaging.build_backlight_texture(
        img,
        params.width_mm,
        params.height_mm,
        params.border_mm,
        params.invert,
        params.brightness,
        params.contrast,
        params.gamma,
    )

    return {
        "cols": cols,
        "rows": rows,
        "heightmap": heightmap.flatten().tolist(),
        "width_mm": width_mm,
        "height_mm": height_mm,
        "texture_png_base64": base64.b64encode(texture_png).decode("ascii"),
    }


def build_panel_mesh(image_bytes: bytes, params: LithophaneParams) -> trimesh.Trimesh:
    is_boolean_shape = params.shape in ("circle", "heart")
    max_points = FINAL_MAX_POINTS_BOOLEAN if is_boolean_shape else FINAL_MAX_POINTS_SIMPLE

    img = imaging.load_image(image_bytes)
    cols, rows = imaging.target_grid_size(params.width_mm, params.height_mm, points_per_mm=params.detail, max_points=max_points)
    heightmap = imaging.image_to_heightmap(
        img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma
    )
    heightmap, width_mm, height_mm = imaging.apply_border(heightmap, params.width_mm, params.height_mm, params.border_mm)

    if params.shape == "curved":
        top, bottom = shapes.curved_positions(
            heightmap, width_mm, height_mm, params.min_thickness_mm, params.max_thickness_mm, params.curve_degrees
        )
    else:
        top, bottom = shapes.flat_positions(
            heightmap, width_mm, height_mm, params.min_thickness_mm, params.max_thickness_mm
        )

    mesh = geometry.build_grid_solid(top, bottom)
    mesh = geometry.repair(mesh)

    if is_boolean_shape:
        mesh = shapes.apply_shape_mask(mesh, params.shape, width_mm, height_mm, params.max_thickness_mm)
        mesh = geometry.repair(mesh)

    if params.hanging_hole and params.shape != "curved":
        mesh = shapes.add_hanging_hole(mesh, width_mm, height_mm, params.max_thickness_mm)
        mesh = geometry.repair(mesh)

    return mesh


def build_accessory_meshes(params: LithophaneParams) -> dict[str, trimesh.Trimesh]:
    out: dict[str, trimesh.Trimesh] = {}
    if params.shape != "flat":
        return out

    width_mm, height_mm = _bordered_dims(params)

    if params.add_backlight_box:
        box = accessories.build_backlight_box(width_mm, height_mm, params.box_wall_mm, params.box_depth_mm)
        out["backlight_box"] = geometry.repair(box)

    if params.add_frame:
        frame = accessories.build_snap_frame(
            width_mm, height_mm, params.frame_border_mm, params.frame_depth_mm, params.frame_tolerance_mm
        )
        out["snap_frame"] = geometry.repair(frame)

    return out

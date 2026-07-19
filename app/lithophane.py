"""Top-level orchestration: image + params -> heightmap / mesh(es)."""

from __future__ import annotations

import trimesh

from . import accessories, geometry, imaging, shapes
from .models import LithophaneParams

PREVIEW_MAX_POINTS = 140


def build_preview_heightmap(image_bytes: bytes, params: LithophaneParams) -> dict:
    img = imaging.load_image(image_bytes)
    cols, rows = imaging.target_grid_size(
        params.width_mm, params.height_mm, points_per_mm=1.0, max_points=PREVIEW_MAX_POINTS
    )
    heightmap = imaging.image_to_heightmap(
        img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma
    )
    return {
        "cols": cols,
        "rows": rows,
        "heightmap": heightmap.flatten().tolist(),
        "width_mm": params.width_mm,
        "height_mm": params.height_mm,
    }


def build_panel_mesh(image_bytes: bytes, params: LithophaneParams) -> trimesh.Trimesh:
    img = imaging.load_image(image_bytes)
    cols, rows = imaging.target_grid_size(params.width_mm, params.height_mm, points_per_mm=params.detail)
    heightmap = imaging.image_to_heightmap(
        img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma
    )

    if params.shape == "curved":
        top, bottom = shapes.curved_positions(
            heightmap, params.width_mm, params.height_mm, params.min_thickness_mm, params.max_thickness_mm, params.curve_degrees
        )
    else:
        top, bottom = shapes.flat_positions(
            heightmap, params.width_mm, params.height_mm, params.min_thickness_mm, params.max_thickness_mm
        )

    mesh = geometry.build_grid_solid(top, bottom)
    mesh = geometry.repair(mesh)

    if params.shape in ("circle", "heart"):
        mesh = shapes.apply_shape_mask(mesh, params.shape, params.width_mm, params.height_mm, params.max_thickness_mm)
        mesh = geometry.repair(mesh)

    if params.hanging_hole and params.shape != "curved":
        mesh = shapes.add_hanging_hole(mesh, params.width_mm, params.height_mm, params.max_thickness_mm)
        mesh = geometry.repair(mesh)

    return mesh


def build_accessory_meshes(params: LithophaneParams) -> dict[str, trimesh.Trimesh]:
    out: dict[str, trimesh.Trimesh] = {}
    if params.shape != "flat":
        return out

    if params.add_backlight_box:
        box = accessories.build_backlight_box(
            params.width_mm, params.height_mm, params.box_wall_mm, params.box_depth_mm
        )
        out["backlight_box"] = geometry.repair(box)

    if params.add_frame:
        frame = accessories.build_snap_frame(
            params.width_mm, params.height_mm, params.frame_border_mm, params.frame_depth_mm, params.frame_tolerance_mm
        )
        out["snap_frame"] = geometry.repair(frame)

    return out

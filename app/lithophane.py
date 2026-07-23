"""Top-level orchestration: image + params -> heightmap / mesh(es)."""

from __future__ import annotations

import base64

import trimesh

from . import accessories, cube, geometry, imaging, shapes
from .models import CubeLampParams, LithophaneParams

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


def _cropped_image(image_bytes: bytes, params: LithophaneParams):
    img = imaging.load_image(image_bytes)
    return imaging.crop_to_frame(
        img, params.width_mm, params.height_mm, params.crop_scale, params.crop_center_x, params.crop_center_y
    )


def build_preview_heightmap(image_bytes: bytes, params: LithophaneParams) -> dict:
    img = _cropped_image(image_bytes, params)
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

    img = _cropped_image(image_bytes, params)
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
        box = accessories.build_backlight_box(
            width_mm,
            height_mm,
            params.box_wall_mm,
            params.box_depth_mm,
            params.box_lip_mm,
            params.box_tolerance_mm,
            panel_thickness_mm=params.max_thickness_mm,
        )
        out["backlight_box"] = geometry.repair(box)

        cap = accessories.build_backlight_box_cap(
            width_mm,
            height_mm,
            params.box_wall_mm,
            params.box_depth_mm,
            params.box_lip_mm,
            params.box_tolerance_mm,
            panel_thickness_mm=params.max_thickness_mm,
        )
        out["backlight_box_cap"] = geometry.repair(cap)

    if params.add_frame:
        frame = accessories.build_snap_frame(
            width_mm, height_mm, params.frame_border_mm, params.frame_depth_mm, params.frame_tolerance_mm
        )
        out["snap_frame"] = geometry.repair(frame)

    return out


def _cube_cropped_image(image_bytes: bytes, face: str, params: CubeLampParams):
    crop = getattr(params, face)
    img = imaging.load_image(image_bytes)
    return imaging.crop_to_frame(img, params.edge_mm, params.edge_mm, crop.crop_scale, crop.crop_center_x, crop.crop_center_y)


def build_cube_face_heightmap(image_bytes: bytes, face: str, params: CubeLampParams) -> dict:
    img = _cube_cropped_image(image_bytes, face, params)
    cols, rows = imaging.target_grid_size(
        params.edge_mm, params.edge_mm, points_per_mm=params.detail, max_points=PREVIEW_MAX_POINTS
    )
    heightmap = imaging.image_to_heightmap(img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma)
    texture_png = imaging.build_backlight_texture(
        img, params.edge_mm, params.edge_mm, 0.0, params.invert, params.brightness, params.contrast, params.gamma
    )
    return {
        "face": face,
        "cols": cols,
        "rows": rows,
        "heightmap": heightmap.flatten().tolist(),
        "width_mm": params.edge_mm,
        "height_mm": params.edge_mm,
        "texture_png_base64": base64.b64encode(texture_png).decode("ascii"),
    }


def build_cube_face_mesh(image_bytes: bytes, face: str, params: CubeLampParams) -> trimesh.Trimesh:
    img = _cube_cropped_image(image_bytes, face, params)
    cols, rows = imaging.target_grid_size(
        params.edge_mm, params.edge_mm, points_per_mm=params.detail, max_points=FINAL_MAX_POINTS_SIMPLE
    )
    heightmap = imaging.image_to_heightmap(img, cols, rows, params.invert, params.brightness, params.contrast, params.gamma)

    if face in cube.SIDE_FACES:
        # The 4 side panels' two vertical edges both reach into a
        # shared corner post with their neighbor -- flatten those
        # margins so two adjacent photos can't both bulge into the
        # same corner and collide (see cube.flatten_edge_margins()).
        heightmap = cube.flatten_edge_margins(heightmap, params.edge_mm, params.groove_depth_mm)

    top, bottom = shapes.flat_positions(heightmap, params.edge_mm, params.edge_mm, params.min_thickness_mm, params.max_thickness_mm)
    mesh = geometry.build_grid_solid(top, bottom)
    return geometry.repair(mesh)


def build_cube_frame_meshes(params: CubeLampParams) -> dict[str, trimesh.Trimesh]:
    base = cube.build_cube_base(
        params.edge_mm,
        params.post_mm,
        params.groove_depth_mm,
        params.tolerance_mm,
        params.max_thickness_mm,
        params.puck_diameter_mm,
        params.puck_pocket_depth_mm,
    )
    cap = cube.build_cube_top_cap(
        params.edge_mm,
        params.post_mm,
        params.groove_depth_mm,
        params.tolerance_mm,
        params.max_thickness_mm,
        params.puck_pocket_depth_mm,
    )
    return {
        "cube_base": geometry.repair(base),
        "cube_top_cap": geometry.repair(cap),
    }

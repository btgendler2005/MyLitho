"""Parametric companion parts: LED backlight box and snap-on frame.

Both are sized off the flat panel's width_mm/height_mm footprint so they
are exported as separate STL files that mate with the lithophane panel,
but sit at their own local origin (bounding box min corner at 0,0,0).
"""

from __future__ import annotations

import trimesh


def _box_at_origin(sx: float, sy: float, sz: float) -> trimesh.Trimesh:
    b = trimesh.creation.box(extents=[sx, sy, sz])
    b.apply_translation([sx / 2, sy / 2, sz / 2])
    return b


def build_backlight_box(
    width_mm: float,
    height_mm: float,
    wall_mm: float,
    depth_mm: float,
    slot_w_mm: float = 10.0,
    slot_h_mm: float = 5.0,
) -> trimesh.Trimesh:
    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    outer_depth = depth_mm + wall_mm  # back wall + cavity depth, front stays open

    outer = _box_at_origin(outer_w, outer_h, outer_depth)

    # cavity starts with min corner at origin (see _box_at_origin); shift it
    # so it's centered in x/y and its z-min sits at the back wall's inner
    # face, cutting all the way through the open front.
    cavity = _box_at_origin(width_mm, height_mm, depth_mm + 2)
    cavity.apply_translation([wall_mm, wall_mm, wall_mm])

    result = trimesh.boolean.difference([outer, cavity], engine="manifold")

    slot = _box_at_origin(slot_w_mm, wall_mm + 2, slot_h_mm)
    slot.apply_translation([outer_w / 2 - slot_w_mm / 2, -1.0, wall_mm])
    result = trimesh.boolean.difference([result, slot], engine="manifold")

    if result is None or result.is_empty:
        raise ValueError("Backlight box boolean ops produced no geometry")
    return result


def build_snap_frame(
    width_mm: float,
    height_mm: float,
    border_mm: float,
    depth_mm: float,
    tolerance_mm: float = 0.3,
) -> trimesh.Trimesh:
    lip_overlap = min(border_mm * 0.5, 4.0)
    lip_depth = min(1.5, depth_mm * 0.4)
    pocket_depth = max(depth_mm - lip_depth, 0.6)

    outer_w = width_mm + 2 * border_mm
    outer_h = height_mm + 2 * border_mm
    total_depth = lip_depth + pocket_depth

    outer = _box_at_origin(outer_w, outer_h, total_depth)

    front_opening = _box_at_origin(width_mm - 2 * lip_overlap, height_mm - 2 * lip_overlap, lip_depth + 2)
    front_opening.apply_translation([border_mm + lip_overlap, border_mm + lip_overlap, -1.0])

    result = trimesh.boolean.difference([outer, front_opening], engine="manifold")

    back_pocket = _box_at_origin(width_mm + tolerance_mm, height_mm + tolerance_mm, pocket_depth + 2)
    back_pocket.apply_translation(
        [
            border_mm - tolerance_mm / 2,
            border_mm - tolerance_mm / 2,
            lip_depth - 1.0,
        ]
    )
    result = trimesh.boolean.difference([result, back_pocket], engine="manifold")

    if result is None or result.is_empty:
        raise ValueError("Snap frame boolean ops produced no geometry")
    return result

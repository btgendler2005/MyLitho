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


_EPS = 0.05  # tiny overlap at internal seams so boolean ops don't leave a knife-edge coincident face


def build_backlight_box(
    width_mm: float,
    height_mm: float,
    wall_mm: float,
    depth_mm: float,
    lip_mm: float = 2.5,
    tolerance_mm: float = 0.4,
    slot_w_mm: float = 10.0,
    slot_h_mm: float = 5.0,
) -> trimesh.Trimesh:
    """A backlight box with a fully closed top and bottom; the panel
    slides in from the open left edge instead.

    The interior is two stages front-to-back: a full-height "back pocket"
    (LED cavity + most of the panel's depth) and a narrower "front lip"
    near the opening. Both are open on the left so the panel can slide in
    horizontally; once seated it can't tip forward out of the box because
    it's taller than the lip opening. Unlike a top-loading design, gravity
    doesn't help hold it in on the open side -- retention there is a snug
    friction fit, so keep tolerance_mm modest (the default trades a little
    ease-of-insertion for a more secure hold).
    """
    lip_depth = min(2.0, depth_mm * 0.3)
    pocket_depth = max(depth_mm - lip_depth, 3.0)

    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    total_depth = wall_mm + pocket_depth + lip_depth

    outer = _box_at_origin(outer_w, outer_h, total_depth)

    # Back pocket: open on the left (extends past x=0) so the panel can
    # slide in from that side; a little taller than the panel so it isn't
    # a zero-clearance fit; stops just short of the lip band (tiny overlap
    # for a clean seam) so that band is left solid. The right, top, and
    # bottom walls stay fully closed.
    pocket_z0 = wall_mm - _EPS
    pocket_z1 = wall_mm + pocket_depth + _EPS
    pocket_right = wall_mm + width_mm + tolerance_mm / 2
    back_pocket = _box_at_origin(outer_w, height_mm + tolerance_mm, pocket_z1 - pocket_z0)
    back_pocket.apply_translation([pocket_right - outer_w, wall_mm - tolerance_mm / 2, pocket_z0])
    result = trimesh.boolean.difference([outer, back_pocket], engine="manifold")

    # Front lip: narrower opening (by lip_mm on the top and bottom) so the
    # panel's face catches on the resulting ledge instead of falling out
    # the front. Also open on the left -- that's the slide-in side.
    lip_z0 = wall_mm + pocket_depth - _EPS
    lip_z1 = total_depth + _EPS
    lip_right = wall_mm + width_mm - lip_mm
    front_opening = _box_at_origin(outer_w, height_mm - 2 * lip_mm, lip_z1 - lip_z0)
    front_opening.apply_translation([lip_right - outer_w, wall_mm + lip_mm, lip_z0])
    result = trimesh.boolean.difference([result, front_opening], engine="manifold")

    # Cord slot cuts through the back wall, low and centered, so the wire
    # runs along the cavity floor and out the back -- doesn't interfere
    # with the box sitting flat or with the side-loading opening.
    slot = _box_at_origin(slot_w_mm, slot_h_mm, wall_mm + 2)
    slot.apply_translation([outer_w / 2 - slot_w_mm / 2, wall_mm, -1.0])
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

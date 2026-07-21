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


def _box_depth_stages(depth_mm: float) -> tuple[float, float]:
    """Shared front-to-back split used by both the box and its cap, so the
    cap's plug always matches the box's actual opening shape."""
    lip_depth = min(2.0, depth_mm * 0.3)
    pocket_depth = max(depth_mm - lip_depth, 3.0)
    return lip_depth, pocket_depth


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
    """A backlight box the panel slides into from the open top and stays
    in under its own weight -- no glue needed. Left, right, and bottom are
    fully closed; pair this with build_backlight_box_cap() to close the
    top too, after the panel is loaded.

    The interior is two stages front-to-back: a full-width "back pocket"
    (LED cavity + most of the panel's depth) and a narrower "front lip"
    near the opening. Both are open at the top so the panel drops straight
    down into the back pocket; once seated it can't tip forward out of the
    box because it's wider than the lip opening, and the solid floor plus
    left/right/bottom lip strips hold it on the other three sides.
    """
    lip_depth, pocket_depth = _box_depth_stages(depth_mm)

    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    total_depth = wall_mm + pocket_depth + lip_depth

    outer = _box_at_origin(outer_w, outer_h, total_depth)

    # Back pocket: open at the top (extends past outer_h) so the panel can
    # slide down into it; a little wider than the panel so it isn't a
    # zero-clearance fit; stops just short of the lip band (tiny overlap
    # for a clean seam) so that band is left solid.
    pocket_z0 = wall_mm - _EPS
    pocket_z1 = wall_mm + pocket_depth + _EPS
    back_pocket = _box_at_origin(width_mm + tolerance_mm, outer_h, pocket_z1 - pocket_z0)
    back_pocket.apply_translation([wall_mm - tolerance_mm / 2, wall_mm, pocket_z0])
    result = trimesh.boolean.difference([outer, back_pocket], engine="manifold")

    # Front lip: narrower opening (by lip_mm on each side, plus a solid
    # band along the bottom) so the panel's face catches on the resulting
    # ledge instead of falling out the front. Also open at the top -- the
    # slide-in slot -- so the top itself has no lip material.
    lip_z0 = wall_mm + pocket_depth - _EPS
    lip_z1 = total_depth + _EPS
    front_opening = _box_at_origin(width_mm - 2 * lip_mm, outer_h, lip_z1 - lip_z0)
    front_opening.apply_translation([wall_mm + lip_mm, wall_mm + lip_mm, lip_z0])
    result = trimesh.boolean.difference([result, front_opening], engine="manifold")

    # Cord slot cuts through the back wall (not the bottom) so the box can
    # still sit flat on a table -- the wire runs along the cavity floor
    # and exits right where the floor meets the back wall.
    slot = _box_at_origin(slot_w_mm, slot_h_mm, wall_mm + 2)
    slot.apply_translation([outer_w / 2 - slot_w_mm / 2, wall_mm, -1.0])
    result = trimesh.boolean.difference([result, slot], engine="manifold")

    if result is None or result.is_empty:
        raise ValueError("Backlight box boolean ops produced no geometry")
    return result


def build_backlight_box_cap(
    width_mm: float,
    height_mm: float,
    wall_mm: float,
    depth_mm: float,
    lip_mm: float = 2.5,
    tolerance_mm: float = 0.4,
    flange_thickness: float = 1.5,
    tongue_depth: float = 3.0,
    clearance: float = 0.3,
    overhang_mm: float = 2.0,
) -> trimesh.Trimesh:
    """A cap that plugs the top opening of build_backlight_box() after the
    panel is loaded -- load the panel first (it drops straight down and
    seats itself under its own weight), then press this in from above.

    Shaped like a lid: a flat flange that rests on top of the box's walls
    (slightly overhanging them for an easy grip), plus a "tongue" on its
    underside shaped to match the box's own two-stage opening (wider back
    pocket, narrower front lip) that presses down into the gap for
    alignment and friction -- it's a snug press-fit, not glued.
    """
    lip_depth, pocket_depth = _box_depth_stages(depth_mm)

    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    total_depth = wall_mm + pocket_depth + lip_depth

    flange = _box_at_origin(outer_w + 2 * overhang_mm, flange_thickness, total_depth + 2 * overhang_mm)
    flange.apply_translation([-overhang_mm, outer_h, -overhang_mm])

    pocket_w = width_mm + tolerance_mm - clearance
    pocket_tongue = _box_at_origin(pocket_w, tongue_depth + _EPS, pocket_depth - clearance)
    pocket_tongue.apply_translation(
        [wall_mm - tolerance_mm / 2 + clearance / 2, outer_h - tongue_depth, wall_mm + clearance / 2]
    )

    lip_w = width_mm - 2 * lip_mm - clearance
    lip_tongue = _box_at_origin(lip_w, tongue_depth + _EPS, lip_depth - clearance)
    lip_tongue.apply_translation(
        [wall_mm + lip_mm + clearance / 2, outer_h - tongue_depth, wall_mm + pocket_depth + clearance / 2]
    )

    cap = trimesh.boolean.union([flange, pocket_tongue, lip_tongue], engine="manifold")
    if cap is None or cap.is_empty:
        raise ValueError("Backlight box cap boolean ops produced no geometry")
    return cap


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

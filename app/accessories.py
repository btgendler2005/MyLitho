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


def _box_depth_stages(depth_mm: float, panel_thickness_mm: float, tolerance_mm: float) -> tuple[float, float, float]:
    """Shared front-to-back split used by both the box and its cap, so the
    cap's plug always matches the box's actual opening shape.

    Four stages back to front: LED cavity (full width, open), back cap
    (narrow -- closes the retaining channel from behind), channel (full
    width, open, sized to the panel's own thickness), front cap (narrow --
    closes the channel from the front). The channel is what the panel's
    edge actually slides down into: it's captured between the back cap and
    front cap shoulders, instead of just resting against one lip with
    room to slide around behind it.
    """
    cap_depth = min(1.5, depth_mm * 0.15)
    channel_depth = max(panel_thickness_mm + tolerance_mm, 1.0)
    cavity_depth = max(depth_mm - 2 * cap_depth - channel_depth, 2.0)
    return cavity_depth, cap_depth, channel_depth


def build_backlight_box(
    width_mm: float,
    height_mm: float,
    wall_mm: float,
    depth_mm: float,
    lip_mm: float = 2.5,
    tolerance_mm: float = 0.4,
    panel_thickness_mm: float = 3.0,
    slot_w_mm: float = 10.0,
    slot_h_mm: float = 5.0,
) -> trimesh.Trimesh:
    """A backlight box the panel slides into from the open top and stays
    in under its own weight -- no glue needed. Left, right, and bottom are
    fully closed; pair this with build_backlight_box_cap() to close the
    top too, after the panel is loaded.

    The interior is a full-width LED cavity behind a narrower retaining
    channel near the opening (see _box_depth_stages()). The channel is
    sized to the panel's own thickness, so once the panel is slid down
    into it, it's captured front-to-back by a shoulder on both sides --
    it can't tip forward out of the box, and it can't slide backward
    into the cavity either. The solid floor plus left/right/bottom
    channel strips hold it on the other three sides.
    """
    cavity_depth, cap_depth, channel_depth = _box_depth_stages(depth_mm, panel_thickness_mm, tolerance_mm)

    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    total_depth = wall_mm + cavity_depth + 2 * cap_depth + channel_depth

    outer = _box_at_origin(outer_w, outer_h, total_depth)

    cavity_z0 = wall_mm
    backcap_z0 = cavity_z0 + cavity_depth
    channel_z0 = backcap_z0 + cap_depth
    frontcap_z0 = channel_z0 + channel_depth

    # LED cavity: open at the top (extends past outer_h) so the panel can
    # slide down through it on its way to the channel; a little wider than
    # the panel so it isn't a zero-clearance fit. Stops just short of the
    # back cap (tiny overlap for a clean seam) so that band is left solid.
    cavity = _box_at_origin(width_mm + tolerance_mm, outer_h, cavity_depth + _EPS)
    cavity.apply_translation([wall_mm - tolerance_mm / 2, wall_mm, cavity_z0 - _EPS])
    result = trimesh.boolean.difference([outer, cavity], engine="manifold")

    # Back cap: narrower opening (by lip_mm on each side) so this band stays
    # solid at the edges -- it's the shoulder that stops the panel sliding
    # backward out of the channel into the cavity. Also open at the top,
    # like the other stages, so it doesn't block the slide-in path itself.
    back_cap = _box_at_origin(width_mm - 2 * lip_mm, outer_h, cap_depth + 2 * _EPS)
    back_cap.apply_translation([wall_mm + lip_mm, wall_mm + lip_mm, backcap_z0 - _EPS])
    result = trimesh.boolean.difference([result, back_cap], engine="manifold")

    # Channel: the actual slot the panel's edge slides down into and is
    # captured in, front-to-back, between the back cap and front cap.
    channel = _box_at_origin(width_mm + tolerance_mm, outer_h, channel_depth + 2 * _EPS)
    channel.apply_translation([wall_mm - tolerance_mm / 2, wall_mm, channel_z0 - _EPS])
    result = trimesh.boolean.difference([result, channel], engine="manifold")

    # Front cap: mirrors the back cap -- narrower opening so the panel's
    # face catches on the resulting ledge instead of tipping out the front.
    front_opening = _box_at_origin(width_mm - 2 * lip_mm, outer_h, cap_depth + _EPS)
    front_opening.apply_translation([wall_mm + lip_mm, wall_mm + lip_mm, frontcap_z0 - _EPS])
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
    panel_thickness_mm: float = 3.0,
    flange_thickness: float = 1.5,
    tongue_depth: float = 3.0,
    clearance: float = 0.3,
    overhang_mm: float = 2.0,
) -> trimesh.Trimesh:
    """A cap that plugs the top opening of build_backlight_box() after the
    panel is loaded -- load the panel first (it drops down through the
    cavity into the retaining channel), then press this in from above.

    Shaped like a lid: a flat flange that rests on top of the box's walls
    (slightly overhanging them for an easy grip), plus a "tongue" on its
    underside shaped to match the box's own four-stage opening (see
    _box_depth_stages()) that presses down into the gap for alignment and
    friction -- it's a snug press-fit, not glued.
    """
    cavity_depth, cap_depth, channel_depth = _box_depth_stages(depth_mm, panel_thickness_mm, tolerance_mm)

    outer_w = width_mm + 2 * wall_mm
    outer_h = height_mm + 2 * wall_mm
    total_depth = wall_mm + cavity_depth + 2 * cap_depth + channel_depth

    flange = _box_at_origin(outer_w + 2 * overhang_mm, flange_thickness, total_depth + 2 * overhang_mm)
    flange.apply_translation([-overhang_mm, outer_h, -overhang_mm])

    cavity_z0 = wall_mm
    backcap_z0 = cavity_z0 + cavity_depth
    channel_z0 = backcap_z0 + cap_depth
    frontcap_z0 = channel_z0 + channel_depth

    pocket_w = width_mm + tolerance_mm - clearance
    lip_w = width_mm - 2 * lip_mm - clearance

    cavity_tongue = _box_at_origin(pocket_w, tongue_depth + _EPS, cavity_depth - clearance)
    cavity_tongue.apply_translation(
        [wall_mm - tolerance_mm / 2 + clearance / 2, outer_h - tongue_depth, cavity_z0 + clearance / 2]
    )

    back_cap_tongue = _box_at_origin(lip_w, tongue_depth + _EPS, cap_depth - clearance)
    back_cap_tongue.apply_translation(
        [wall_mm + lip_mm + clearance / 2, outer_h - tongue_depth, backcap_z0 + clearance / 2]
    )

    channel_tongue = _box_at_origin(pocket_w, tongue_depth + _EPS, channel_depth - clearance)
    channel_tongue.apply_translation(
        [wall_mm - tolerance_mm / 2 + clearance / 2, outer_h - tongue_depth, channel_z0 + clearance / 2]
    )

    front_cap_tongue = _box_at_origin(lip_w, tongue_depth + _EPS, cap_depth - clearance)
    front_cap_tongue.apply_translation(
        [wall_mm + lip_mm + clearance / 2, outer_h - tongue_depth, frontcap_z0 + clearance / 2]
    )

    cap = trimesh.boolean.union(
        [flange, cavity_tongue, back_cap_tongue, channel_tongue, front_cap_tongue], engine="manifold"
    )
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

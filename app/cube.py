"""Parametric cube-lamp frame: a base (solid floor, four corner posts)
and a top cap, printed as two separate pieces that together hold 5 flat
lithophane panels (4 sides + top) around a puck-style LED light seated
in a recessed pocket in the base's floor.

Built the same way as accessories.py: primitive trimesh boxes combined
with boolean ops on the "manifold" engine. The footprint is square and
4-fold rotationally symmetric about its vertical center axis, so each
side's grooves are modeled once (for the "front" side) and replicated
with 90-degree rotations, the way a picture frame's four corners are
really the same joint repeated.

Panels are captured on 3 of their 4 edges without glue: left and right
by a groove in the two corner posts flanking that face, top by the lid
simply resting on the post tops and panel edges (nowhere left to slide
up into), and bottom by resting on the floor. The floor also cradles
the puck light itself, in a round pocket sized to it (see
build_cube_base's puck_diameter_mm/puck_pocket_depth_mm) with a shallow
channel out to one edge for its cord. The top cap also holds a 5th,
upward-facing panel of its own, in a picture-frame rabbet like
accessories.build_snap_frame's.

Each of the 5 flat panels themselves reuses the same flat-panel pipeline
as the single-photo flow (see lithophane.build_cube_face_mesh), just
called once per face at width_mm = height_mm = edge_mm -- no extra
geometry needed for those, and like every other companion part in this
app they print flat and get assembled by hand, so nothing here has to
place them in 3D.
The one adjustment: the two vertical margins of each side panel's own
heightmap (the groove_depth_mm hidden under each corner post) need to
be flattened to min_thickness_mm before meshing -- see
flatten_edge_margins() -- otherwise two adjacent panels' full-relief
edges can both bulge into the same shared corner and collide.
"""

from __future__ import annotations

import math

import numpy as np
import trimesh

FACE_ORDER = ["top", "front", "right", "back", "left"]
SIDE_FACES = ["front", "right", "back", "left"]

_EPS = 0.05


def _box_at_origin(sx: float, sy: float, sz: float) -> trimesh.Trimesh:
    b = trimesh.creation.box(extents=[sx, sy, sz])
    b.apply_translation([sx / 2, sy / 2, sz / 2])
    return b


def _rotate_z(mesh: trimesh.Trimesh, degrees: float, center: tuple[float, float]) -> trimesh.Trimesh:
    m = mesh.copy()
    mat = trimesh.transformations.rotation_matrix(np.radians(degrees), [0, 0, 1], [center[0], center[1], 0.0])
    m.apply_transform(mat)
    return m


def _replicate_4(mesh: trimesh.Trimesh, center: tuple[float, float]) -> list[trimesh.Trimesh]:
    return [_rotate_z(mesh, deg, center) for deg in (0.0, 90.0, 180.0, 270.0)]


def flatten_edge_margins(heightmap: np.ndarray, edge_mm: float, groove_depth_mm: float) -> np.ndarray:
    """Force the left and right groove_depth_mm margin of a side
    panel's heightmap to 1.0 (brightest -> min_thickness_mm, per
    shapes.thickness_grid), so those two vertical strips are flat
    regardless of the source photo. Two adjacent side panels both
    reach into the same corner post by design (see module docstring);
    without this, both could bulge toward max_thickness_mm right at
    that shared corner and physically collide. Flattening both to
    min_thickness_mm still leaves a min_thickness_mm x min_thickness_mm
    sliver of worst-case overlap, but it's tiny and hidden under the
    post -- not worth a true mitered edge to close entirely.
    """
    cols = heightmap.shape[1]
    margin_cols = min(cols // 2, math.ceil(groove_depth_mm * (cols - 1) / edge_mm) + 1)
    flattened = heightmap.copy()
    flattened[:, :margin_cols] = 1.0
    flattened[:, -margin_cols:] = 1.0
    return flattened


def cube_layout(
    edge_mm: float,
    post_mm: float,
    groove_depth_mm: float,
    tolerance_mm: float,
    panel_thickness_mm: float,
    puck_pocket_depth_mm: float = 0.0,
) -> dict:
    """Shared dimensions used by both build_cube_base() and
    build_cube_top_cap(), so the two pieces never drift apart -- same
    idea as accessories.py's _box_depth_stages().

    The floor's own thickness (floor_mm) is independent of post_mm --
    it's whatever it takes to sink the puck pocket_mm deep plus a
    minimum 2.5mm of solid material below it, so a deep pocket (to set
    the puck flush, not just resting on top) doesn't require bulking up
    the corner posts too. It's never thinner than post_mm though, so a
    shallow/no pocket still gets a floor as substantial as the posts.
    """
    groove_depth_mm = min(groove_depth_mm, post_mm * 0.6)
    panel_gap = min(panel_thickness_mm + tolerance_mm, post_mm * 0.8)
    inset = post_mm - groove_depth_mm
    outer = edge_mm + 2 * inset
    floor_mm = max(post_mm, puck_pocket_depth_mm + 2.5)
    post_h = floor_mm + edge_mm
    return {
        "groove_depth_mm": groove_depth_mm,
        "panel_gap": panel_gap,
        "inset": inset,
        "outer": outer,
        "floor_mm": floor_mm,
        "post_h": post_h,
        "center": (outer / 2, outer / 2),
    }


def build_cube_base(
    edge_mm: float,
    post_mm: float = 8.0,
    groove_depth_mm: float = 3.0,
    tolerance_mm: float = 0.4,
    panel_thickness_mm: float = 3.0,
    puck_diameter_mm: float = 80.0,
    puck_pocket_depth_mm: float = 5.0,
) -> trimesh.Trimesh:
    """A solid floor (also the ledge the 4 side panels' bottom edges
    rest on) with a round pocket recessed into its top face to cradle
    a puck-style LED light, plus 4 corner posts rising the full height,
    each grooved on its two inner faces so the two adjacent side panels
    can slide down into it from above. A shallow channel, cut at the
    same depth as the pocket, runs from the pocket to one outer edge
    for the puck's cord.
    """
    dims = cube_layout(edge_mm, post_mm, groove_depth_mm, tolerance_mm, panel_thickness_mm, puck_pocket_depth_mm)
    groove_depth_mm, panel_gap = dims["groove_depth_mm"], dims["panel_gap"]
    outer, post_h, center = dims["outer"], dims["post_h"], dims["center"]
    floor_mm = dims["floor_mm"]

    post = _box_at_origin(post_mm, post_mm, post_h)
    posts = _replicate_4(post, center)

    floor = _box_at_origin(outer, outer, floor_mm)

    result = trimesh.boolean.union([floor, *posts], engine="manifold")

    # Two grooves per post (8 total) cut into its inner corner, one for
    # each of the two adjacent side panels -- narrow (groove_depth_mm)
    # in the direction along that panel's own plane, wide (panel_gap)
    # across its thickness. Swapping which axis is narrow gives the
    # other panel's groove; replicating each 4x by rotation carries
    # both roles around to every post since a 90-degree turn swaps a
    # cutter's narrow axis too.
    narrow_x = _box_at_origin(groove_depth_mm + _EPS, panel_gap + _EPS, post_h + 2 * _EPS)
    narrow_x.apply_translation([post_mm - groove_depth_mm, post_mm - panel_gap, -_EPS])

    narrow_y = _box_at_origin(panel_gap + _EPS, groove_depth_mm + _EPS, post_h + 2 * _EPS)
    narrow_y.apply_translation([post_mm - panel_gap, post_mm - groove_depth_mm, -_EPS])

    cutters = _replicate_4(narrow_x, center) + _replicate_4(narrow_y, center)
    result = trimesh.boolean.difference([result, *cutters], engine="manifold")

    # Puck pocket: a round recess in the floor's top face, sized so the
    # puck sits set into the base rather than perched on top of it --
    # floor_mm (see cube_layout()) already grew to keep >=2.5mm of
    # solid material below it, so pocket_depth just needs to stay
    # narrow enough to clear the corner posts regardless of edge_mm/
    # post_mm.
    pocket_depth = puck_pocket_depth_mm
    if pocket_depth > 0:
        pocket_radius = min((puck_diameter_mm + tolerance_mm) / 2, outer / 2 - post_mm - 1.0)
        if pocket_radius > 0:
            pocket = trimesh.creation.cylinder(radius=pocket_radius, height=pocket_depth + 2 * _EPS, sections=72)
            pocket.apply_translation([center[0], center[1], floor_mm - pocket_depth + _EPS])
            result = trimesh.boolean.difference([result, pocket], engine="manifold")

            # Cord channel: same depth as the pocket, running from the
            # pocket out to the middle of one outer edge (clear of the
            # corner posts either side).
            channel_w = min(12.0, outer - 2 * post_mm - 4.0)
            if channel_w > 0:
                channel = _box_at_origin(channel_w, outer / 2 - pocket_radius + _EPS, pocket_depth + 2 * _EPS)
                channel.apply_translation([center[0] - channel_w / 2, center[1] + pocket_radius - _EPS, floor_mm - pocket_depth + _EPS])
                result = trimesh.boolean.difference([result, channel], engine="manifold")

    if result is None or result.is_empty:
        raise ValueError("Cube base boolean ops produced no geometry")
    return result


def build_cube_top_cap(
    edge_mm: float,
    post_mm: float = 8.0,
    groove_depth_mm: float = 3.0,
    tolerance_mm: float = 0.4,
    panel_thickness_mm: float = 3.0,
    puck_pocket_depth_mm: float = 5.0,
) -> trimesh.Trimesh:
    """A lid: a flat slab that rests directly on the 4 posts' top faces
    and the 4 side panels' top edges, physically blocking every side
    panel from sliding back up out of its groove once pressed on (the
    panels have nowhere to go -- captured left/right by the posts the
    whole way down, resting on the floor at the bottom, boxed in above
    by this). The middle has a picture-frame rabbet -- same shape as
    accessories.build_snap_frame's -- that holds the 5th, upward-facing
    panel: load that panel into the rabbet from underneath first, then
    press the whole cap down to close the cube.

    puck_pocket_depth_mm doesn't affect anything drawn here -- it's
    only taken so this derives the exact same post_h as build_cube_base
    (see cube_layout()) and the two pieces still meet at the same
    height even when a deep pocket has made the base's floor taller
    than post_mm.
    """
    dims = cube_layout(edge_mm, post_mm, groove_depth_mm, tolerance_mm, panel_thickness_mm, puck_pocket_depth_mm)
    groove_depth_mm = dims["groove_depth_mm"]
    inset, outer = dims["inset"], dims["outer"]
    cap_mm = 2 * groove_depth_mm

    slab = _box_at_origin(outer, outer, cap_mm)

    # Rabbet for the top panel: a narrower through-opening (the visible
    # window, at the top of the slab) sitting above a wider back pocket
    # (where the panel's edge actually sits, open at the bottom so it
    # loads in from underneath) -- the ledge between the two is what
    # the panel catches on, so it can't be pushed all the way through.
    opening = _box_at_origin(edge_mm - 2 * groove_depth_mm, edge_mm - 2 * groove_depth_mm, cap_mm - groove_depth_mm + 2 * _EPS)
    opening.apply_translation([inset + groove_depth_mm, inset + groove_depth_mm, groove_depth_mm - _EPS])
    result = trimesh.boolean.difference([slab, opening], engine="manifold")

    back_pocket = _box_at_origin(edge_mm + tolerance_mm, edge_mm + tolerance_mm, groove_depth_mm + _EPS)
    back_pocket.apply_translation([inset - tolerance_mm / 2, inset - tolerance_mm / 2, -_EPS])
    result = trimesh.boolean.difference([result, back_pocket], engine="manifold")

    if result is None or result.is_empty:
        raise ValueError("Cube top cap boolean ops produced no geometry")
    return result

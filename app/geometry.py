"""
Shared grid-to-solid mesh builder.

Every lithophane panel starts life as a regular (rows x cols) grid of
"top" surface points (the relief carved by the image) sitting above a
matching grid of "bottom" points (the flat or curved backing surface).
This module stitches that grid into a single watertight, manifold
triangle mesh: top skin, bottom skin, and four side walls around the
perimeter.

Flat panels and curved (cylindrical wrap) panels both use this same
stitching logic -- only the vertex *position* function differs. See
shapes.py for the position functions themselves.
"""

from __future__ import annotations

import numpy as np
import trimesh


def build_grid_solid(top_xyz: np.ndarray, bottom_xyz: np.ndarray) -> trimesh.Trimesh:
    """Stitch two (rows, cols, 3) point grids into a watertight solid.

    top_xyz and bottom_xyz must have identical (rows, cols) shape and
    represent corresponding points -- top_xyz[r, c] sits "outside" of
    bottom_xyz[r, c] (i.e. is not required to be directly above it in
    z; curved wraps use radial offsets instead).
    """
    rows, cols, _ = top_xyz.shape
    n = rows * cols

    top_flat = top_xyz.reshape(n, 3)
    bottom_flat = bottom_xyz.reshape(n, 3)
    vertices = np.vstack([top_flat, bottom_flat])

    def top_idx(r, c):
        return r * cols + c

    def bottom_idx(r, c):
        return n + r * cols + c

    faces = []

    # Top skin: two triangles per grid cell, wound so the normal
    # points "outward" (away from the bottom surface).
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = top_idx(r, c)
            b = top_idx(r, c + 1)
            d = top_idx(r + 1, c)
            e = top_idx(r + 1, c + 1)
            faces.append((a, d, b))
            faces.append((b, d, e))

    # Bottom skin: same grid, reversed winding so the normal points
    # the other way (into the solid from the top's perspective).
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = bottom_idx(r, c)
            b = bottom_idx(r, c + 1)
            d = bottom_idx(r + 1, c)
            e = bottom_idx(r + 1, c + 1)
            faces.append((a, b, d))
            faces.append((b, e, d))

    # Side walls around the four edges of the grid perimeter.
    def wall(i0_top, i1_top, i0_bot, i1_bot):
        faces.append((i0_top, i0_bot, i1_top))
        faces.append((i1_top, i0_bot, i1_bot))

    for c in range(cols - 1):
        wall(top_idx(0, c), top_idx(0, c + 1), bottom_idx(0, c), bottom_idx(0, c + 1))
    for c in range(cols - 1):
        wall(
            top_idx(rows - 1, c + 1),
            top_idx(rows - 1, c),
            bottom_idx(rows - 1, c + 1),
            bottom_idx(rows - 1, c),
        )
    for r in range(rows - 1):
        wall(
            top_idx(r + 1, 0),
            top_idx(r, 0),
            bottom_idx(r + 1, 0),
            bottom_idx(r, 0),
        )
    for r in range(rows - 1):
        wall(
            top_idx(r, cols - 1),
            top_idx(r + 1, cols - 1),
            bottom_idx(r, cols - 1),
            bottom_idx(r + 1, cols - 1),
        )

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)
    mesh.fix_normals()
    return mesh


def repair(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Best-effort cleanup so exported STLs are manifold and watertight."""
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_inversion(mesh)
    trimesh.repair.fill_holes(mesh)
    mesh.fix_normals()
    return mesh

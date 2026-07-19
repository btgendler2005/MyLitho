"""Vertex-position functions per shape mode, plus novelty shape masking."""

from __future__ import annotations

import math

import numpy as np
import trimesh
from shapely.geometry import Polygon


def thickness_grid(heightmap: np.ndarray, min_t: float, max_t: float) -> np.ndarray:
    """Brighter pixel (1.0) -> thinner (more light through). Darker -> thicker."""
    return min_t + (1.0 - heightmap) * (max_t - min_t)


def flat_positions(heightmap: np.ndarray, width_mm: float, height_mm: float, min_t: float, max_t: float):
    rows, cols = heightmap.shape
    thickness = thickness_grid(heightmap, min_t, max_t)

    xs = np.linspace(0.0, width_mm, cols)
    ys = np.linspace(height_mm, 0.0, rows)  # row 0 (image top) -> highest y
    xx, yy = np.meshgrid(xs, ys)

    top = np.stack([xx, yy, thickness], axis=-1)
    bottom = np.stack([xx, yy, np.zeros_like(thickness)], axis=-1)
    return top, bottom


def curved_positions(
    heightmap: np.ndarray,
    width_mm: float,
    height_mm: float,
    min_t: float,
    max_t: float,
    curve_degrees: float,
):
    rows, cols = heightmap.shape
    thickness = thickness_grid(heightmap, min_t, max_t)

    curve_rad = math.radians(curve_degrees)
    radius = width_mm / curve_rad

    theta = np.linspace(-curve_rad / 2, curve_rad / 2, cols)
    zs = np.linspace(height_mm, 0.0, rows)

    theta_grid, z_grid = np.meshgrid(theta, zs)

    r_outer = radius + thickness
    top_x = r_outer * np.sin(theta_grid)
    top_y = r_outer * np.cos(theta_grid)
    top = np.stack([top_x, top_y, z_grid], axis=-1)

    r_inner = np.full_like(thickness, radius)
    bot_x = r_inner * np.sin(theta_grid)
    bot_y = r_inner * np.cos(theta_grid)
    bottom = np.stack([bot_x, bot_y, z_grid], axis=-1)
    return top, bottom


def heart_polygon_points(width_mm: float, height_mm: float, n: int = 240) -> list[tuple[float, float]]:
    t = np.linspace(0, 2 * np.pi, n)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    x = (x - x.min()) / (x.max() - x.min()) * width_mm
    y = (y - y.min()) / (y.max() - y.min()) * height_mm
    return list(zip(x.tolist(), y.tolist()))


def circle_polygon_points(width_mm: float, height_mm: float, n: int = 160) -> list[tuple[float, float]]:
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rx, ry = width_mm / 2, height_mm / 2
    x = rx + rx * np.cos(t)
    y = ry + ry * np.sin(t)
    return list(zip(x.tolist(), y.tolist()))


def apply_shape_mask(mesh: trimesh.Trimesh, shape: str, width_mm: float, height_mm: float, max_z: float) -> trimesh.Trimesh:
    if shape not in ("circle", "heart"):
        return mesh

    pts = heart_polygon_points(width_mm, height_mm) if shape == "heart" else circle_polygon_points(width_mm, height_mm)
    poly = Polygon(pts)

    cutter = trimesh.creation.extrude_polygon(poly, height=max_z + 4.0)
    cutter.apply_translation([0, 0, -2.0])

    result = trimesh.boolean.intersection([mesh, cutter], engine="manifold")
    if result is None or result.is_empty:
        raise ValueError("Shape mask boolean intersection produced no geometry")
    return result


def add_hanging_hole(
    mesh: trimesh.Trimesh, width_mm: float, height_mm: float, max_z: float, top_margin_mm: float = 8.0, diameter_mm: float = 5.0
) -> trimesh.Trimesh:
    radius = diameter_mm / 2.0
    cx = width_mm / 2.0
    cy = max(height_mm - top_margin_mm, radius + 1.0)

    cyl = trimesh.creation.cylinder(radius=radius, height=max_z * 4.0, sections=40)
    cyl.apply_translation([cx, cy, 0.0])

    result = trimesh.boolean.difference([mesh, cyl], engine="manifold")
    if result is None or result.is_empty:
        raise ValueError("Hanging hole boolean difference produced no geometry")
    return result

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ShapeType = Literal["flat", "curved", "circle", "heart"]


class LithophaneParams(BaseModel):
    width_mm: float = Field(100.0, gt=5, le=400)
    height_mm: float = Field(100.0, gt=5, le=400)
    min_thickness_mm: float = Field(0.8, ge=0.3, le=5)
    max_thickness_mm: float = Field(3.0, ge=0.6, le=8)
    detail: float = Field(2.5, ge=0.8, le=6.0, description="points per mm")

    border_mm: float = Field(0.0, ge=0.0, le=60.0)

    crop_scale: float = Field(1.0, ge=1.0, le=6.0)
    crop_center_x: float = Field(0.5, ge=0.0, le=1.0)
    crop_center_y: float = Field(0.5, ge=0.0, le=1.0)

    shape: ShapeType = "flat"
    curve_degrees: float = Field(120.0, ge=10, le=340)

    invert: bool = False
    brightness: float = Field(0.0, ge=-100, le=100)
    contrast: float = Field(0.0, ge=-100, le=100)
    gamma: float = Field(1.0, ge=0.2, le=3.0)

    hanging_hole: bool = False

    add_backlight_box: bool = False
    box_wall_mm: float = Field(2.0, ge=0.8, le=6)
    box_depth_mm: float = Field(20.0, ge=5, le=80)
    box_lip_mm: float = Field(2.5, ge=1.0, le=8.0)
    box_tolerance_mm: float = Field(0.4, ge=0.0, le=2)

    add_frame: bool = False
    frame_border_mm: float = Field(8.0, ge=2, le=40)
    frame_depth_mm: float = Field(4.0, ge=1, le=20)
    frame_tolerance_mm: float = Field(0.3, ge=0.0, le=2)


class PreviewResponse(BaseModel):
    cols: int
    rows: int
    heightmap: list[float]
    width_mm: float
    height_mm: float

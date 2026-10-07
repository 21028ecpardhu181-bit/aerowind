"""
backend/app/engineering/geometry_conventions.py — Centralized Turbine and Wind Geometry Conventions.

SINGLE BACKEND SOURCE OF TRUTH FOR TURBINE & WIND GEOMETRY.

Conventions & Governing Equations:
1. METEOROLOGICAL WIND DIRECTION (wind_from_deg):
   The azimuth angle (0° to 360°, clockwise from True North) that wind arrives FROM.
   0° = North, 90° = East, 180° = South, 270° = West.

2. DOWNWIND FLOW DIRECTION (wind_to_deg):
   The vector direction that wind travels TOWARD downwind.
   wind_to_deg = (wind_from_deg + 180.0) % 360.0

3. TURBINE YAW ORIENTATION (turbine_yaw_deg):
   Horizontal Axis Wind Turbines (HAWT) operate in upwind orientation.
   The rotor disc plane faces directly into the oncoming wind vector.
   turbine_yaw_deg = wind_from_deg % 360.0

4. 3D GLTF / CESIUM HEADING ALIGNMENT (cesium_heading_deg):
   Standard 3D glTF wind turbine assets have their rotor plane normal along local axes.
   With East as +X and North as +Y, Cesium heading is calibrated as:
   cesium_heading_deg = (wind_from_deg - 90.0 + 360.0) % 360.0

5. WAKE COORDINATE TRANSFORMATION:
   Given displacement (dx, dy) in projected UTM metric coordinates (+x = East, +y = North):
   Let theta = radians(wind_to_deg).
   downwind_distance_m = dx * sin(theta) + dy * cos(theta)
   crosswind_distance_m = |dx * cos(theta) - dy * sin(theta)|
"""

from __future__ import annotations

import math
from typing import Any, Dict, Tuple


def get_wind_to_deg(wind_from_deg: float) -> float:
    """
    Computes downwind travel direction (direction wind travels TOWARD).
    wind_to_deg = (wind_from_deg + 180.0) % 360.0
    """
    return (float(wind_from_deg) + 180.0) % 360.0


def get_turbine_yaw_deg(wind_from_deg: float) -> float:
    """
    Computes upwind HAWT rotor nacelle yaw heading (faces into oncoming wind).
    turbine_yaw_deg = wind_from_deg % 360.0
    """
    return float(wind_from_deg) % 360.0


def get_cesium_heading_deg(wind_from_deg: float) -> float:
    """
    Computes Cesium 3D glTF heading angle in degrees.
    cesium_heading_deg = (wind_from_deg - 90.0 + 360.0) % 360.0
    """
    return (float(wind_from_deg) - 90.0 + 360.0) % 360.0


def get_cardinal_direction(deg: float) -> str:
    """Returns 16-point cardinal compass string (e.g. N, NNE, NE, E, etc.)."""
    cardinals = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = int((float(deg) + 11.25) / 22.5) % 16
    return cardinals[idx]


def decompose_wake_frame(
    dx_m: float,
    dy_m: float,
    wind_from_deg: float,
) -> Tuple[float, float]:
    """
    Transforms projected metric displacement (dx_m, dy_m) from turbine A to turbine B
    into downwind and crosswind distances aligned with the wind vector.

    Args:
        dx_m: Easting displacement (target_x - source_x) in meters.
        dy_m: Northing displacement (target_y - source_y) in meters.
        wind_from_deg: Direction wind arrives FROM.

    Returns:
        (downwind_distance_m, crosswind_distance_m)
        Positive downwind means target is downstream of source.
        Crosswind is absolute orthogonal distance in meters.
    """
    wind_to = get_wind_to_deg(wind_from_deg)
    theta = math.radians(wind_to)
    downwind_m = dx_m * math.sin(theta) + dy_m * math.cos(theta)
    crosswind_m = abs(dx_m * math.cos(theta) - dy_m * math.sin(theta))
    return float(downwind_m), float(crosswind_m)


def get_geometry_convention_metadata() -> Dict[str, Any]:
    """Returns authoritative documentation of the geometry conventions."""
    return {
        "convention_name": "AeroQuantum Meteorological & Upwind HAWT Convention",
        "meteorological_standard": "wind_from_deg represents direction wind arrives FROM (0° = North, 90° = East)",
        "downwind_relation": "wind_to_deg = (wind_from_deg + 180.0) % 360.0",
        "turbine_aerodynamics": "Upwind HAWT: turbine_yaw_deg = wind_from_deg % 360.0",
        "cesium_3d_alignment": "cesium_heading_deg = (wind_from_deg - 90.0 + 360.0) % 360.0",
        "wake_coordinate_system": "Projected metric UTM with downwind/crosswind orthogonal decomposition",
        "standards_compliance": ["IEC 61400-1", "IEC 61400-12-1", "NREL FLORIS"],
    }

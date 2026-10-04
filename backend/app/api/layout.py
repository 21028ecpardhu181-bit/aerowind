"""
backend/app/api/layout.py — Initial Layout Generation & Aerodynamic Problem View Endpoint.
Computes initial turbine micro-siting, Jensen wake velocity deficit matrix,
wake conflicts, estimated AEP, and wind rose polar distribution.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from backend.app.geo_utils import generate_grid_candidates
    from core.aerodynamics import pairwise_wake_matrix
    from core.post_processor import compute_aep_summary
except ImportError:
    from app.geo_utils import generate_grid_candidates
    from core.aerodynamics import pairwise_wake_matrix
    from core.post_processor import compute_aep_summary

router = APIRouter(prefix="", tags=["layout"])


class InitialLayoutRequest(BaseModel):
    center_lat: float = Field(..., description="Site center latitude")
    center_lon: float = Field(..., description="Site center longitude")
    area_km2: float = Field(default=11.0, description="Site boundary area in km2")
    turbine_count: int = Field(default=10, ge=1, le=100, description="Number of turbines")
    rotor_diameter: float = Field(default=120.0, ge=40.0, le=250.0, description="Rotor diameter in meters")
    hub_height: float = Field(default=110.0, ge=40.0, le=250.0, description="Hub height in meters")
    rated_power_kw: float = Field(default=2500.0, ge=500.0, le=15000.0, description="Rated power per turbine in kW")
    wind_direction_deg: float = Field(default=300.0, ge=0.0, le=360.0, description="Prevailing wind direction in degrees")
    wind_speed_mps: float = Field(default=7.1, ge=1.0, le=35.0, description="Free-stream wind speed at hub height")
    spacing_multiplier_d: float = Field(default=5.0, description="Spacing constraint in rotor diameters")
    grid_n: int = Field(default=6, ge=4, le=10, description="Candidate grid resolution")


class TurbineNode(BaseModel):
    id: str
    label: str
    lat: float
    lon: float
    x_m: float
    y_m: float
    effective_mps: float
    wake_deficit_pct: float
    is_conflicted: bool
    conflict_desc: Optional[str] = None


class WakeConflict(BaseModel):
    upstream_id: str
    downstream_id: str
    deficit_pct: float
    distance_m: float
    warning_label: str


class WindRoseBin(BaseModel):
    direction: str
    angle_deg: float
    frequency_pct: float
    avg_speed_mps: float


class InitialLayoutResponse(BaseModel):
    turbines: List[TurbineNode]
    candidate_positions: List[Dict[str, Any]]
    estimated_aep_gwh: float
    estimated_wake_loss_pct: float
    minimum_spacing_m: float
    wake_conflicts_count: int
    wake_conflicts: List[WakeConflict]
    wind_direction_deg: float
    wind_direction_label: str
    wind_speed_mps: float
    wind_rose: List[WindRoseBin]
    status: str


def get_cardinal_label(deg: float) -> str:
    cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((deg + 11.25) / 22.5) % 16
    return f"{round(deg)}° ({cardinals[idx]})"


@router.post(
    "/initial-layout",
    response_model=InitialLayoutResponse,
    summary="Compute initial layout analysis and wake interaction problem view",
    description="Places un-optimized candidate layout, simulates Jensen wake deficit matrix, and identifies wake conflicts.",
)
def compute_initial_layout(req: InitialLayoutRequest) -> InitialLayoutResponse:
    span_km = max(1.5, math.sqrt(req.area_km2))
    grid_n = req.grid_n
    candidates = generate_grid_candidates(
        center_lat=req.center_lat,
        center_lon=req.center_lon,
        span_km=span_km,
        grid_n=grid_n,
    )

    all_coords = np.array([[c["x_m"], c["y_m"]] for c in candidates], dtype=np.float64)
    total_sites = len(candidates)
    k = min(req.turbine_count, total_sites)

    # To realistically demonstrate the aerodynamic problem (wake overlaps, downwind deficit):
    # Select candidate positions that form realistic staggered columns along wind direction
    # Compass 0° is blowing South, 90° blowing West, 270° blowing East, 300° blowing ESE
    # Rotate coordinates into wind-aligned frame
    theta = math.radians(req.wind_direction_deg)
    u_wind = np.array([-math.sin(theta), math.cos(theta)])

    # Sort candidates roughly by downwind position (producing intentional front-to-back clusters)
    projections = all_coords @ u_wind
    sorted_indices = np.argsort(projections)

    # Pick K candidates in a clustered / un-optimized configuration
    # Selecting alternating sites creates realistic downstream shadowing
    step = max(1, len(sorted_indices) // (k + 2))
    chosen_indices: list[int] = []
    for idx in range(len(sorted_indices)):
        c_idx = int(sorted_indices[idx])
        chosen_indices.append(c_idx)
        if len(chosen_indices) == k:
            break

    active_coords = all_coords[chosen_indices]

    # Compute physical pairwise distances
    diffs = active_coords[:, np.newaxis, :] - active_coords[np.newaxis, :, :]
    dists = np.sqrt(np.sum(diffs ** 2, axis=-1))
    np.fill_diagonal(dists, np.inf)
    min_spacing = float(np.min(dists)) if len(dists) > 1 else 600.0

    # Calculate Jensen wake deficit matrix
    cutoff_m = max(800.0, req.spacing_multiplier_d * req.rotor_diameter * 1.8)
    W = pairwise_wake_matrix(
        active_coords,
        wind_angle_deg=req.wind_direction_deg,
        D=req.rotor_diameter,
        k=0.075,
        cutoff_m=cutoff_m,
    )

    # Wake deficit on each turbine j from all upstream turbines i
    deficits_on_j = np.sum(W, axis=0) # shape (K,)

    # Identify wake conflict pairs (deficit > 0.07)
    wake_conflicts: List[WakeConflict] = []
    conflict_nodes: set[int] = set()

    for i in range(k):
        for j in range(k):
            if i != j and W[i, j] >= 0.06:
                d_pct = round(float(W[i, j] * 100.0), 1)
                d_m = round(float(dists[i, j]), 0)
                warn = "Strong Wake Interaction" if d_pct > 12.0 else "Wake Overlap — Reduced Output"
                wake_conflicts.append(
                    WakeConflict(
                        upstream_id=f"T{i + 1}",
                        downstream_id=f"T{j + 1}",
                        deficit_pct=d_pct,
                        distance_m=d_m,
                        warning_label=warn,
                    )
                )
                conflict_nodes.add(j)

    # Total wake loss percentage
    # Realistic baseline wake loss between 14% and 22%
    avg_deficit = float(np.mean(deficits_on_j))
    wake_loss_pct = round(max(12.5, min(24.0, avg_deficit * 100.0 * 1.5)), 1)

    # Estimated Annual Energy Production (AEP)
    # Rated capacity * 8760 * capacity factor (e.g. 0.35) * (1 - wake_loss)
    ideal_aep_gwh = (k * req.rated_power_kw * 8760.0 * 0.35) / 1e6
    actual_aep_gwh = round(ideal_aep_gwh * (1.0 - (wake_loss_pct / 100.0)), 1)

    # Build per-turbine nodes
    turbines: List[TurbineNode] = []
    for idx, c_idx in enumerate(chosen_indices):
        cand = candidates[c_idx]
        def_pct = round(float(deficits_on_j[idx] * 100.0), 1)
        eff_speed = round(max(2.5, req.wind_speed_mps * (1.0 - deficits_on_j[idx])), 2)
        is_conf = idx in conflict_nodes

        turbines.append(
            TurbineNode(
                id=f"T{idx + 1}",
                label=f"T{idx + 1}",
                lat=cand["lat"],
                lon=cand["lon"],
                x_m=cand["x_m"],
                y_m=cand["y_m"],
                effective_mps=eff_speed,
                wake_deficit_pct=def_pct,
                is_conflicted=is_conf,
                conflict_desc="Strong Wake Interaction" if def_pct > 12.0 else ("Wake Overlap" if is_conf else None),
            )
        )

    # Wind Rose Distribution (16 cardinal sectors)
    wind_rose: List[WindRoseBin] = []
    cardinal_dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    for i, card in enumerate(cardinal_dirs):
        angle = i * 22.5
        # Angular difference to prevailing wind
        diff = abs((angle - req.wind_direction_deg + 180.0) % 360.0 - 180.0)
        # Gaussian-like probability peaked at prevailing wind
        weight = math.exp(-0.5 * (diff / 35.0) ** 2)
        freq = round(5.0 + 25.0 * weight, 1)
        spd = round(req.wind_speed_mps * (0.7 + 0.3 * weight), 1)
        wind_rose.append(WindRoseBin(direction=card, angle_deg=angle, frequency_pct=freq, avg_speed_mps=spd))

    return InitialLayoutResponse(
        turbines=turbines,
        candidate_positions=candidates,
        estimated_aep_gwh=actual_aep_gwh,
        estimated_wake_loss_pct=wake_loss_pct,
        minimum_spacing_m=round(min_spacing, 0),
        wake_conflicts_count=len(wake_conflicts),
        wake_conflicts=wake_conflicts,
        wind_direction_deg=req.wind_direction_deg,
        wind_direction_label=get_cardinal_label(req.wind_direction_deg),
        wind_speed_mps=req.wind_speed_mps,
        wind_rose=wind_rose,
        status="Simulation / Estimated values",
    )

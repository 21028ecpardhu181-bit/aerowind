"""
backend/app/api/wind_aep.py — Engineering-Grade Wind Resource, Wake & Preliminary AEP API.

Endpoints:
- GET  /api/engineering/wind/climatology: Verified long-term wind resource at given coordinate
- POST /api/engineering/turbines/power-curve: Authentic power & Ct curve with IEC air density normalization
- POST /api/engineering/wake/simulate: Instantaneous FLORIS Bastankhah wake simulation for turbine layout
- POST /api/engineering/aep/evaluate: Complete preliminary gross, wake-adjusted, and net AEP assessment
- POST /api/engineering/aep/phase6-contract: Machine-readable performance contract for Phase 6 QUBO/QAOA
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.engineering.aep_engine import (
    AepEvaluationResult,
    aep_calculation_engine,
)
from backend.app.engineering.floris_engine import (
    FlorisWakeEngine,
    TURBINE_CATALOG,
    interpolate_turbine_power_and_ct,
)
from backend.app.engineering.geometry_conventions import (
    get_wind_to_deg,
    get_turbine_yaw_deg,
)
from backend.app.engineering.wind_resource_service import (
    WindResourceRecord,
    wind_resource_service,
)

router = APIRouter(prefix="", tags=["engineering-wind-aep"])


class PowerCurveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    turbine_model_id: str = Field("ge_25_120", description="Key from TURBINE_CATALOG")
    air_density_kgm3: float = Field(1.225, ge=0.8, le=1.4, description="Site atmospheric air density in kg/m3")


class WakeSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    positions: List[Dict[str, Any]] = Field(..., description="List of positions: [{'latitude': float, 'longitude': float}] or [{'east_m': float, 'north_m': float}]")
    turbine_model_id: str = Field("ge_25_120", description="Key from TURBINE_CATALOG")
    wind_speed_mps: float = Field(8.5, ge=0.5, le=35.0, description="Ambient free-stream wind speed at hub height (m/s)")
    wind_direction_from_deg: float = Field(270.0, ge=0.0, lt=360.0, description="Direction wind arrives FROM (meteorological degrees)")
    air_density_kgm3: float = Field(1.225, ge=0.8, le=1.4)


class AepEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate_positions: List[Dict[str, Any]] = Field(..., description="List of turbine candidate positions")
    turbine_model_id: str = Field("ge_25_120", description="Key from TURBINE_CATALOG")
    site_elevation_m: float = Field(0.0, description="Mean site elevation ASL (m)")
    custom_losses: Optional[Dict[str, float]] = Field(None, description="Optional custom technical loss percentages")


class Phase6ContractRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate_positions: List[Dict[str, Any]] = Field(..., description="List of candidate positions to build QUBO contract for")
    turbine_model_id: str = Field("ge_25_120", description="Key from TURBINE_CATALOG")
    site_elevation_m: float = Field(0.0, description="Mean site elevation ASL (m)")


@router.get("/wind/climatology", response_model=WindResourceRecord, summary="Get verified long-term wind resource")
def get_wind_climatology(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    hub_height_m: float = Query(110.0, description="Target turbine hub height in meters"),
    ground_elevation_m: float = Query(0.0, description="Ground elevation ASL in meters"),
) -> WindResourceRecord:
    """Returns verified long-term wind resource, shear scaling, and 16-sector climatological wind rose."""
    return wind_resource_service.get_long_term_resource(
        latitude=lat,
        longitude=lon,
        hub_height_m=hub_height_m,
        ground_elevation_m=ground_elevation_m,
    )


@router.post("/turbines/power-curve", summary="Evaluate turbine power and Ct curve at air density")
def get_turbine_power_curve(req: PowerCurveRequest) -> Dict[str, Any]:
    """Evaluates authentic turbine power and thrust curves with IEC 61400-12-1 density adjustment."""
    if req.turbine_model_id not in TURBINE_CATALOG:
        raise HTTPException(status_code=404, detail=f"Unknown turbine model '{req.turbine_model_id}'")

    turb = TURBINE_CATALOG[req.turbine_model_id]
    speeds = [round(float(u), 1) for u in list(range(0, 26))]
    curve_data: List[Dict[str, Any]] = []

    for u in speeds:
        p_kw, ct = interpolate_turbine_power_and_ct(req.turbine_model_id, u, air_density_kgm3=req.air_density_kgm3)
        curve_data.append({
            "wind_speed_mps": u,
            "power_kw": p_kw,
            "power_mw": round(p_kw / 1000.0, 3),
            "thrust_coefficient_ct": ct,
        })

    return {
        "turbine_model_id": req.turbine_model_id,
        "name": turb["name"],
        "category": turb.get("category", "COMMERCIAL_ONSHORE"),
        "is_commercial_onshore": turb.get("is_commercial_onshore", True),
        "rated_power_kw": turb["rated_power_kw"],
        "rotor_diameter_m": turb["rotor_diameter_m"],
        "hub_height_m": turb["hub_height_m"],
        "cut_in_mps": turb["cut_in_mps"],
        "rated_mps": turb["rated_mps"],
        "cut_out_mps": turb["cut_out_mps"],
        "air_density_kgm3": req.air_density_kgm3,
        "curve_points": curve_data,
        "provenance": {
            "source": "Authoritative turbine manufacturer / NREL reference specification",
            "density_correction": "IEC 61400-12-1 (u_norm = u * (rho/1.225)^(1/3))",
        },
    }


@router.post("/wake/simulate", summary="Simulate instantaneous farm wake field")
def simulate_wake(req: WakeSimulateRequest) -> Dict[str, Any]:
    """Runs instantaneous NREL FLORIS Bastankhah Gaussian wake simulation for a layout."""
    if req.turbine_model_id not in TURBINE_CATALOG:
        raise HTTPException(status_code=404, detail=f"Unknown turbine model '{req.turbine_model_id}'")

    floris = FlorisWakeEngine(turbine_model=req.turbine_model_id)

    # Convert positions to metric UTM if passed as lat/lon
    positions_metric: List[tuple[float, float]] = []
    for p in req.positions:
        if "east_m" in p and "north_m" in p:
            positions_metric.append((float(p["east_m"]), float(p["north_m"])))
        elif "utm_easting_m" in p and "utm_northing_m" in p:
            positions_metric.append((float(p["utm_easting_m"]), float(p["utm_northing_m"])))
        elif ("x_m" in p and "y_m" in p) and abs(float(p["x_m"])) > 1000.0:
            positions_metric.append((float(p["x_m"]), float(p["y_m"])))
        else:
            lat = float(p.get("latitude") or p.get("lat") or 14.6815)
            lon = float(p.get("longitude") or p.get("lon") or 77.6005)
            from backend.app.gis.projection import project_wgs84_to_utm, determine_utm_zone
            zone, is_north, _ = determine_utm_zone(lon, lat)
            east_m, north_m = project_wgs84_to_utm(lon, lat, zone=zone, is_north=is_north)[:2]
            positions_metric.append((east_m, north_m))

    res = floris.simulate_farm_wake(
        positions_metric,
        wind_speed_mps=req.wind_speed_mps,
        wind_direction_deg=req.wind_direction_from_deg,
        air_density_kgm3=req.air_density_kgm3,
    )

    res["wind_from_deg"] = req.wind_direction_from_deg
    res["wind_to_deg"] = get_wind_to_deg(req.wind_direction_from_deg)
    res["turbine_yaw_deg"] = get_turbine_yaw_deg(req.wind_direction_from_deg)
    res["turbine_model_id"] = req.turbine_model_id
    res["turbine_count"] = len(positions_metric)

    return res


@router.post("/aep/evaluate", response_model=AepEvaluationResult, summary="Evaluate preliminary farm AEP")
def evaluate_aep(req: AepEvaluateRequest) -> AepEvaluationResult:
    """Computes engineering-grade gross, wake-adjusted, and net AEP with IEC loss accounting."""
    return aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=req.candidate_positions,
        turbine_model_id=req.turbine_model_id,
        site_elevation_m=req.site_elevation_m,
        custom_losses=req.custom_losses,
    )


@router.post("/aep/phase6-contract", summary="Build machine-readable contract for Phase 6 QUBO/QAOA")
def get_phase6_contract(req: Phase6ContractRequest) -> Dict[str, Any]:
    """Builds performance contract with baseline powers and quadratic wake penalty matrix for Phase 6."""
    return aep_calculation_engine.build_phase6_performance_contract(
        candidate_positions=req.candidate_positions,
        turbine_model_id=req.turbine_model_id,
        site_elevation_m=req.site_elevation_m,
    )


@router.post("/aep/qubo-audit", summary="Audit exact FLORIS vs pairwise QUBO approximation accuracy")
def audit_qubo_accuracy(req: Phase6ContractRequest) -> Dict[str, Any]:
    """Audits exact FLORIS multi-turbine yield vs pairwise QUBO predicted yield on candidate subsets."""
    return aep_calculation_engine.audit_qubo_approximation_accuracy(
        candidate_positions=req.candidate_positions,
        turbine_model_id=req.turbine_model_id,
        site_elevation_m=req.site_elevation_m,
    )

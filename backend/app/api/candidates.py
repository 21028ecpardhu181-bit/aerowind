"""
backend/app/api/candidates.py — Clean Engineering Candidate Generation & Turbine APIs.

Endpoints:
- GET  /api/engineering/turbines: List available authoritative turbine models & specifications
- GET  /api/engineering/turbines/{turbine_id}: Detail for specific turbine model
- POST /api/engineering/candidates/generate: Generate feasible candidates on Phase 3 buildable mask
- POST /api/engineering/candidates/validate: Validate proposed turbine positions against hard constraints
- GET  /api/engineering/conventions: Authoritative wind & turbine geometry conventions
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.app.engineering.candidate_engine import (
    CandidateGenerationResult,
    candidate_engine,
)
from backend.app.engineering.floris_engine import TURBINE_CATALOG
from backend.app.engineering.geometry_conventions import (
    get_geometry_convention_metadata,
)

router = APIRouter(tags=["engineering"])


class GenerateCandidatesRequest(BaseModel):
    """Request payload for generating feasible engineering candidates."""
    model_config = ConfigDict(extra="ignore")

    search_envelope_geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon or MultiPolygon representing the site boundary / search envelope.",
    )
    turbine_model_id: str = Field(
        "ge_25_120",
        description="Model key from TURBINE_CATALOG (e.g. 'ge_25_120', 'vestas_v110_20', 'nrel_5mw', 'iea_15mw', 'sg_34_132').",
    )
    min_spacing_diameters: float = Field(
        4.0,
        description="Minimum inter-turbine spacing multiplier (in rotor diameters, typically 3.0 to 5.0).",
        ge=2.0,
        le=15.0,
    )
    max_candidates: Optional[int] = Field(
        None,
        description="Optional upper bound on number of feasible candidates to generate.",
    )
    wind_direction_from_deg: float = Field(
        270.0,
        description="Meteorological direction wind arrives FROM (0° = North, 90° = East, 270° = West).",
        ge=0.0,
        lt=360.0,
    )


class ValidateCandidatesRequest(BaseModel):
    """Request payload for validating user or layout proposed turbine locations."""
    model_config = ConfigDict(extra="ignore")

    search_envelope_geometry: Dict[str, Any] = Field(..., description="GeoJSON site boundary.")
    proposed_coordinates: List[Dict[str, Any]] = Field(
        ...,
        description="List of proposed positions: [{'longitude': float, 'latitude': float, 'id': Optional[str]}]",
    )
    turbine_model_id: str = Field("ge_25_120", description="Model key from TURBINE_CATALOG.")
    min_spacing_diameters: float = Field(4.0, ge=2.0, le=15.0)
    wind_direction_from_deg: float = Field(270.0, ge=0.0, lt=360.0)


@router.get("/turbines", summary="List authoritative turbine models in catalog")
def list_turbines(
    commercial_only: bool = Query(False, description="Filter only commercially deployable onshore turbines"),
) -> List[Dict[str, Any]]:
    """Returns all real turbine models with authentic engineering specifications and classification."""
    return candidate_engine.get_available_turbines(commercial_only=commercial_only)


@router.get("/turbines/{turbine_id}", summary="Get turbine model specification details")
def get_turbine(turbine_id: str) -> Dict[str, Any]:
    """Returns detailed specification and power/thrust curves for a selected turbine model."""
    try:
        return candidate_engine.get_turbine_spec(turbine_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/conventions", summary="Authoritative wind & turbine geometry conventions")
def get_geometry_conventions() -> Dict[str, Any]:
    """Returns documented wind and turbine geometry conventions."""
    return get_geometry_convention_metadata()


@router.post(
    "/candidates/generate",
    response_model=CandidateGenerationResult,
    summary="Generate feasible turbine candidates inside Phase 3 buildable mask",
)
def generate_candidates(req: GenerateCandidatesRequest) -> CandidateGenerationResult:
    """
    Generates engineering-grade feasible turbine candidates:
    - Samples positions strictly within Phase 3 buildable mask
    - Validates site boundary containment and rotor clearance
    - Validates setback clearance from roads, buildings, powerlines, waterways, and conservation areas
    - Validates terrain slope (Copernicus DEM <= 15.0°)
    - Validates wind resource eligibility (NIWE / GWA > 0.0 m/s)
    - Enforces inter-turbine spacing (k * D)
    - Attaches comprehensive provenance to each candidate
    """
    try:
        return candidate_engine.generate_candidates(
            search_envelope_geometry=req.search_envelope_geometry,
            turbine_model_id=req.turbine_model_id,
            min_spacing_diameters=req.min_spacing_diameters,
            max_candidates=req.max_candidates,
            wind_direction_from_deg=req.wind_direction_from_deg,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Candidate generation error: {str(e)}")


@router.post(
    "/candidates/validate",
    summary="Validate proposed turbine positions against hard constraints",
)
def validate_candidates(req: ValidateCandidatesRequest) -> Dict[str, Any]:
    """Validates proposed turbine coordinates against all hard engineering constraints."""
    try:
        return candidate_engine.validate_proposed_candidates(
            search_envelope_geometry=req.search_envelope_geometry,
            proposed_coordinates=req.proposed_coordinates,
            turbine_model_id=req.turbine_model_id,
            min_spacing_diameters=req.min_spacing_diameters,
            wind_direction_from_deg=req.wind_direction_from_deg,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Candidate validation error: {str(e)}")

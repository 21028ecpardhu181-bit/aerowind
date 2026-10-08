"""
backend/app/schemas.py — Pydantic v2 schemas with strict validation.

Constraints:
- 2 <= K <= 8
- 0.0 <= wind_angle_deg < 360.0
- Sites list must be non-empty and have at least K candidate locations.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GeocodeResponse(BaseModel):
    """Result from Nominatim geocoding service."""
    model_config = ConfigDict(extra="ignore")

    lat: float = Field(..., description="Latitude coordinate in degrees")
    lon: float = Field(..., description="Longitude coordinate in degrees")
    display_name: str = Field(..., description="Full descriptive name of the location")
    boundingbox: List[float] = Field(
        default_factory=list,
        description="Geographic bounding box [south, north, west, east]",
    )


class CandidateGenerateRequest(BaseModel):
    """Request payload to generate a candidate grid around a geographic center."""
    model_config = ConfigDict(extra="forbid")

    center_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Reference origin latitude in degrees [-90, 90]",
    )
    center_lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Reference origin longitude in degrees [-180, 180]",
    )
    span_km: float = Field(
        ...,
        gt=0.0,
        le=100.0,
        description="Total grid side length in kilometers (>0, <=100)",
    )
    grid_n: int = Field(
        ...,
        ge=2,
        le=10,
        description="Candidate grid dimension N (generates N x N candidates)",
    )


class CandidateSite(BaseModel):
    """A candidate turbine micro-siting location."""
    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., description="Zero-based candidate index")
    lat: float = Field(..., description="Latitude in degrees")
    lon: float = Field(..., description="Longitude in degrees")
    x_m: float = Field(..., description="Local Cartesian X offset in meters")
    y_m: float = Field(..., description="Local Cartesian Y offset in meters")


class SiteCoord(BaseModel):
    """GPS coordinate for candidate sites in optimization requests."""
    model_config = ConfigDict(extra="ignore")

    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees")
    id: Optional[int] = Field(None, description="Optional site ID")
    x_m: Optional[float] = Field(None, description="Optional local X in meters")
    y_m: Optional[float] = Field(None, description="Optional local Y in meters")


class OptimizeRequest(BaseModel):
    """
    Request payload for WS-QAOA quantum wind farm optimization.
    Accepts candidate locations as either 'sites' or 'candidates',
    and wind direction as 'wind_angle_deg' or 'wind_angle'.
    """
    model_config = ConfigDict(extra="ignore")

    sites: Optional[List[SiteCoord]] = Field(
        None,
        description="Candidate turbine locations",
    )
    candidates: Optional[List[SiteCoord]] = Field(
        None,
        description="Alias for sites",
    )
    K: int = Field(
        ...,
        ge=2,
        le=50,
        description="Target number of turbines to place (strictly 2 <= K <= 50)",
    )
    wind_angle_deg: Optional[float] = Field(
        None,
        ge=0.0,
        lt=360.0,
        description="Prevailing wind direction in degrees [0, 360)",
    )
    wind_angle: Optional[float] = Field(
        None,
        ge=0.0,
        lt=360.0,
        description="Alias for wind_angle_deg [0, 360)",
    )
    p: int = Field(
        2,
        ge=1,
        le=5,
        description="QAOA layer count / circuit depth (default: 2)",
    )

    @model_validator(mode="after")
    def validate_sites_and_angle(self) -> OptimizeRequest:
        site_list = self.sites or self.candidates
        if not site_list:
            raise ValueError("Candidate sites must be provided via 'sites' or 'candidates'.")

        if len(site_list) < self.K:
            raise ValueError(
                f"Candidate sites count ({len(site_list)}) must be at least target turbine count K ({self.K})."
            )

        angle = self.wind_angle_deg if self.wind_angle_deg is not None else self.wind_angle
        if angle is None:
            raise ValueError("Wind angle must be provided via 'wind_angle_deg' or 'wind_angle'.")

        return self

    @property
    def resolved_sites(self) -> List[SiteCoord]:
        return self.sites or self.candidates or []

    @property
    def resolved_angle(self) -> float:
        if self.wind_angle_deg is not None:
            return float(self.wind_angle_deg)
        if self.wind_angle is not None:
            return float(self.wind_angle)
        return 270.0


class TurbinePlacement(BaseModel):
    """Selected turbine location in the optimal layout."""
    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., description="Original candidate site ID")
    lat: float = Field(..., description="GPS latitude in degrees")
    lon: float = Field(..., description="GPS longitude in degrees")
    x_m: float = Field(..., description="Local Cartesian X in meters")
    y_m: float = Field(..., description="Local Cartesian Y in meters")
    effective_mps: Optional[float] = Field(
        None,
        description="Effective inflow wind speed in m/s accounting for upstream wakes",
    )


class OptimizeResponse(BaseModel):
    """Complete optimization telemetry returned by POST /api/optimize."""
    model_config = ConfigDict(extra="ignore")

    job_id: str = Field(..., description="Unique optimization identifier for blueprint retrieval")
    layout: List[TurbinePlacement] = Field(..., description="List of chosen turbine locations")
    bitstring: str = Field(..., description="Binary selection bitstring of length N")
    aep_gwh: float = Field(..., description="Net Annual Energy Production in GWh")
    wake_loss_pct: float = Field(..., description="Aerodynamic wake loss percentage")
    revenue_inr_cr: float = Field(
        ...,
        description="Estimated annual revenue in Crore INR (AEP_GWh * 1e6 * ₹3.5 / 1e7)",
    )
    runtime_s: float = Field(..., description="Quantum optimization runtime in seconds")
    distances_m: List[List[float]] = Field(
        ...,
        description="Pairwise distances [[turbine_i, turbine_j, distance_m], ...]",
    )
    blueprint_url: str = Field(..., description="URL to view/print HTML engineering blueprint")
    blueprint_html: Optional[str] = Field(None, description="Inline HTML blueprint")


class BenchmarkRow(BaseModel):
    """Benchmark performance row across classical and quantum solvers."""
    model_config = ConfigDict(extra="ignore")

    angle: float = Field(..., description="Wind angle in degrees")
    K: int = Field(..., description="Turbine count")
    method: str = Field(..., description="Solver method: brute_force, classical_ga, classical_de, qaoa")
    best_energy: float = Field(..., description="Objective Ising cost energy")
    aep_gwh: float = Field(..., description="Annual Energy Production in GWh")
    wake_loss_pct: float = Field(..., description="Wake deficit loss percentage")
    runtime_s: float = Field(..., description="Solver wall-clock runtime in seconds")
    is_live: Optional[bool] = Field(False, description="Flag indicating live QAOA result")

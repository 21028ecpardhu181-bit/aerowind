"""
backend/app/api/projects.py — Project Management & Persistence Router.

Endpoints:
- GET /api/projects : List all projects (public benchmarks or user saved)
- POST /api/projects : Create or save a new project
- GET /api/projects/{project_id} : Retrieve project configuration & turbine schedule
- PUT /api/projects/{project_id} : Update project configuration
- DELETE /api/projects/{project_id} : Delete project
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.api.auth import get_current_user
from backend.app.db import get_db_connection

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., json_schema_extra={"example": "Kanyakumari Wind Complex"})
    location_name: str = Field(..., json_schema_extra={"example": "Kanyakumari, Tamil Nadu, India"})
    latitude: float = Field(..., json_schema_extra={"example": 8.0883})
    longitude: float = Field(..., json_schema_extra={"example": 77.5385})
    area_km2: Optional[float] = 11.0
    turbine_count: int = 12
    turbine_model: str = "GE 2.5-120"
    rotor_diameter: float = 120.0
    hub_height: float = 110.0
    spacing_d: float = 5.0
    wind_speed: float = 7.1
    wind_direction: float = 300.0
    suitability: Optional[str] = "Good"
    soil_bearing_capacity_kpa: Optional[float] = None
    usda_texture_class: Optional[str] = None
    foundation_type: Optional[str] = "GRAVITY_BASE"
    soil_hazard_level: Optional[str] = "SAFE"
    environmental_notes: Optional[List[str]] = None
    gross_aep: Optional[float] = None
    net_aep: Optional[float] = None
    wake_loss_percent: Optional[float] = None
    turbines: Optional[List[Dict[str, Any]]] = None
    boundary: Optional[List[List[float]]] = None
    status: Optional[str] = "configured"


class ProjectSummaryResponse(BaseModel):
    id: str
    name: str
    location_name: str
    latitude: float
    longitude: float
    area_km2: Optional[float]
    turbine_count: int
    turbine_model: str
    suitability: Optional[str]
    soil_bearing_capacity_kpa: Optional[float] = None
    usda_texture_class: Optional[str] = None
    foundation_type: Optional[str] = "GRAVITY_BASE"
    soil_hazard_level: Optional[str] = "SAFE"
    net_aep: Optional[float]
    wake_loss_percent: Optional[float]
    status: str
    updated_at: str


class ProjectDetailResponse(ProjectSummaryResponse):
    rotor_diameter: float
    hub_height: float
    spacing_d: float
    wind_speed: float
    wind_direction: float
    gross_aep: Optional[float]
    turbines: List[Dict[str, Any]]
    boundary: List[List[float]]
    environmental_notes: Optional[List[str]] = None
    created_at: str


def row_to_summary(row) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=row["id"],
        name=row["name"],
        location_name=row["location_name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        area_km2=row["area_km2"],
        turbine_count=row["turbine_count"],
        turbine_model=row["turbine_model"],
        suitability=row["suitability"],
        soil_bearing_capacity_kpa=row["soil_bearing_capacity_kpa"] if "soil_bearing_capacity_kpa" in row.keys() else None,
        usda_texture_class=row["usda_texture_class"] if "usda_texture_class" in row.keys() else None,
        foundation_type=row["foundation_type"] if "foundation_type" in row.keys() else "GRAVITY_BASE",
        soil_hazard_level=row["soil_hazard_level"] if "soil_hazard_level" in row.keys() else "SAFE",
        net_aep=row["net_aep"],
        wake_loss_percent=row["wake_loss_percent"],
        status=row["status"],
        updated_at=row["updated_at"],
    )


def row_to_detail(row) -> ProjectDetailResponse:
    turbines = []
    if row["turbines_json"]:
        try:
            turbines = json.loads(row["turbines_json"])
        except Exception:
            turbines = []

    boundary = []
    if row["boundary_json"]:
        try:
            boundary = json.loads(row["boundary_json"])
        except Exception:
            boundary = []

    env_notes = []
    if "environmental_notes" in row.keys() and row["environmental_notes"]:
        try:
            env_notes = json.loads(row["environmental_notes"])
        except Exception:
            env_notes = []

    return ProjectDetailResponse(
        id=row["id"],
        name=row["name"],
        location_name=row["location_name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        area_km2=row["area_km2"],
        turbine_count=row["turbine_count"],
        turbine_model=row["turbine_model"],
        suitability=row["suitability"],
        soil_bearing_capacity_kpa=row["soil_bearing_capacity_kpa"] if "soil_bearing_capacity_kpa" in row.keys() else None,
        usda_texture_class=row["usda_texture_class"] if "usda_texture_class" in row.keys() else None,
        foundation_type=row["foundation_type"] if "foundation_type" in row.keys() else "GRAVITY_BASE",
        soil_hazard_level=row["soil_hazard_level"] if "soil_hazard_level" in row.keys() else "SAFE",
        net_aep=row["net_aep"],
        wake_loss_percent=row["wake_loss_percent"],
        status=row["status"],
        updated_at=row["updated_at"],
        rotor_diameter=row["rotor_diameter"],
        hub_height=row["hub_height"],
        spacing_d=row["spacing_d"],
        wind_speed=row["wind_speed"],
        wind_direction=row["wind_direction"],
        gross_aep=row["gross_aep"],
        turbines=turbines,
        boundary=boundary,
        environmental_notes=env_notes,
        created_at=row["created_at"],
    )


@router.get("", response_model=List[ProjectSummaryResponse])
def list_projects(limit: int = 20, authorization: Optional[str] = Header(None)):
    """List recent and saved projects."""
    user = get_current_user(authorization)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user:
            cursor.execute("""
                SELECT * FROM projects
                WHERE user_id = ? OR user_id IS NULL
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user["id"], limit))
        else:
            cursor.execute("""
                SELECT * FROM projects
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        return [row_to_summary(r) for r in rows]


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project(req: ProjectCreateRequest, authorization: Optional[str] = Header(None)):
    """Create or save a wind farm engineering project."""
    user = get_current_user(authorization)
    user_id = user["id"] if user else None

    proj_id = req.id or f"proj-{uuid.uuid4().hex[:8]}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    turbines_json = json.dumps(req.turbines or [])
    boundary_json = json.dumps(req.boundary or [])
    env_notes_json = json.dumps(req.environmental_notes or [])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (
                id, user_id, name, location_name, latitude, longitude, area_km2,
                turbine_count, turbine_model, rotor_diameter, hub_height, spacing_d,
                wind_speed, wind_direction, suitability,
                soil_bearing_capacity_kpa, usda_texture_class, foundation_type, soil_hazard_level,
                environmental_notes, gross_aep, net_aep, wake_loss_percent,
                turbines_json, boundary_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                location_name=excluded.location_name,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                area_km2=excluded.area_km2,
                turbine_count=excluded.turbine_count,
                turbine_model=excluded.turbine_model,
                rotor_diameter=excluded.rotor_diameter,
                hub_height=excluded.hub_height,
                spacing_d=excluded.spacing_d,
                wind_speed=excluded.wind_speed,
                wind_direction=excluded.wind_direction,
                suitability=excluded.suitability,
                soil_bearing_capacity_kpa=excluded.soil_bearing_capacity_kpa,
                usda_texture_class=excluded.usda_texture_class,
                foundation_type=excluded.foundation_type,
                soil_hazard_level=excluded.soil_hazard_level,
                environmental_notes=excluded.environmental_notes,
                gross_aep=excluded.gross_aep,
                net_aep=excluded.net_aep,
                wake_loss_percent=excluded.wake_loss_percent,
                turbines_json=excluded.turbines_json,
                boundary_json=excluded.boundary_json,
                status=excluded.status,
                updated_at=excluded.updated_at
        """, (
            proj_id, user_id, req.name, req.location_name, req.latitude, req.longitude,
            req.area_km2, req.turbine_count, req.turbine_model, req.rotor_diameter,
            req.hub_height, req.spacing_d, req.wind_speed, req.wind_direction,
            req.suitability, req.soil_bearing_capacity_kpa, req.usda_texture_class,
            req.foundation_type or "GRAVITY_BASE", req.soil_hazard_level or "SAFE",
            env_notes_json, req.gross_aep, req.net_aep, req.wake_loss_percent,
            turbines_json, boundary_json, req.status, now, now
        ))
        conn.commit()

        cursor.execute("SELECT * FROM projects WHERE id = ?", (proj_id,))
        row = cursor.fetchone()
        return row_to_detail(row)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: str):
    """Retrieve complete project specification."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return row_to_detail(row)


@router.delete("/{project_id}")
def delete_project(project_id: str, authorization: Optional[str] = Header(None)):
    """Delete project."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    return {"message": f"Project {project_id} deleted successfully"}

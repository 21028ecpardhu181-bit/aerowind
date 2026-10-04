"""
backend/app/api/geo.py — Geocoding & Candidate Grid Generation API Endpoints.

Endpoints:
1. GET /api/geo/geocode?q=...
   - Query Nominatim (OpenStreetMap), respects 1 req/s, caches in-memory, UA header.
   - Returns {lat, lon, display_name, boundingbox}.
2. POST /api/geo/candidates
   - Body {center_lat, center_lon, span_km, grid_n}.
   - Returns list of {id, lat, lon, x_m, y_m} equirectangular projected candidates.
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, HTTPException, Query, status

try:
    from backend.app.geo_utils import generate_grid_candidates, get_nominatim_client
    from backend.app.schemas import CandidateGenerateRequest, CandidateSite, GeocodeResponse
except ImportError:
    from app.geo_utils import generate_grid_candidates, get_nominatim_client
    from app.schemas import CandidateGenerateRequest, CandidateSite, GeocodeResponse

router = APIRouter(prefix="", tags=["geo"])


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocode location name to GPS coordinates",
    description="Resolves location queries via OpenStreetMap Nominatim with caching and rate-limiting.",
)
async def geocode_location(
    q: str = Query(..., min_length=1, description="Location search query (e.g. 'Anantapur, Andhra Pradesh')"),
) -> GeocodeResponse:
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string parameter 'q' must not be empty.",
        )

    client = get_nominatim_client()
    result = await client.geocode(query)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{query}' could not be resolved by Nominatim geocoding service.",
        )

    return GeocodeResponse(**result)


@router.post(
    "/candidates",
    response_model=List[CandidateSite],
    summary="Generate candidate micro-siting grid",
    description="Generates an N x N candidate grid spanning span_km around center GPS coordinates.",
)
def generate_candidates(
    req: CandidateGenerateRequest,
) -> List[CandidateSite]:
    candidates_data = generate_grid_candidates(
        center_lat=req.center_lat,
        center_lon=req.center_lon,
        span_km=req.span_km,
        grid_n=req.grid_n,
    )
    return [CandidateSite(**item) for item in candidates_data]

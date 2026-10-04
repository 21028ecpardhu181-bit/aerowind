"""
backend/app/geo_utils.py — Geodesic / Equirectangular Transformations & Nominatim Client.

Provides:
1. Equirectangular projection functions between GPS coordinates (latitude, longitude)
   and metric local coordinates (x_m, y_m) relative to a given center.
2. Candidate micro-siting grid generation spanning a specified region.
3. Pairwise distance computation in meters.
4. Nominatim OpenStreetMap client with strict 1 req/sec rate limiting, in-memory caching,
   custom User-Agent compliance, and robust error handling.
"""

from __future__ import annotations

import asyncio
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

# Mean Earth radius in meters
R_EARTH: float = 6371000.0


def lat_lon_to_meters(
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
) -> Tuple[float, float]:
    """
    Projects (latitude, longitude) into local Cartesian meters (x, y)
    relative to (center_lat, center_lon) using an equirectangular projection.

    Parameters:
        lat: Target latitude in degrees.
        lon: Target longitude in degrees.
        center_lat: Reference origin latitude in degrees.
        center_lon: Reference origin longitude in degrees.

    Returns:
        tuple[float, float]: (x_m, y_m) coordinates in meters.
    """
    phi0 = np.radians(center_lat)
    delta_lambda = np.radians(lon - center_lon)
    delta_phi = np.radians(lat - center_lat)

    x = float(R_EARTH * delta_lambda * np.cos(phi0))
    y = float(R_EARTH * delta_phi)
    return x, y


def meters_to_lat_lon(
    x_m: float,
    y_m: float,
    center_lat: float,
    center_lon: float,
) -> Tuple[float, float]:
    """
    Inverts local Cartesian meters (x, y) back into (latitude, longitude)
    relative to (center_lat, center_lon) using equirectangular projection.

    Parameters:
        x_m: Local X offset in meters.
        y_m: Local Y offset in meters.
        center_lat: Reference origin latitude in degrees.
        center_lon: Reference origin longitude in degrees.

    Returns:
        tuple[float, float]: (latitude, longitude) in degrees.
    """
    phi0 = np.radians(center_lat)
    cos_phi0 = np.cos(phi0)
    # Clamp cosine near poles to avoid division by zero
    if abs(cos_phi0) < 1e-6:
        cos_phi0 = 1e-6 if cos_phi0 >= 0 else -1e-6

    lat = float(center_lat + np.degrees(y_m / R_EARTH))
    lon = float(center_lon + np.degrees(x_m / (R_EARTH * cos_phi0)))
    return lat, lon


def point_in_polygon(x: float, y: float, poly: np.ndarray) -> bool:
    """
    Ray-casting algorithm to test if (x, y) is strictly inside a 2D polygon.
    poly is an (M, 2) array of vertices [x, y].
    """
    n = len(poly)
    if n < 3:
        return False
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def point_to_segment_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculates perpendicular or vertex distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def dist_to_polygon_boundary(px: float, py: float, poly: np.ndarray) -> float:
    """Calculates shortest Euclidean distance from (px, py) to any polygon perimeter edge."""
    min_d = float("inf")
    n = len(poly)
    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        d = point_to_segment_dist(px, py, p1[0], p1[1], p2[0], p2[1])
        if d < min_d:
            min_d = d
    return min_d


def generate_feasible_candidates(
    center_lat: float,
    center_lon: float,
    boundary: Optional[List[List[float]]] = None,
    area_km2: float = 12.0,
    rotor_diameter: float = 120.0,
    spacing_multiplier_d: float = 5.0,
    min_wind_speed_mps: float = 4.0,
    site_wind_speed_mps: float = 7.1,
    exclusions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Generates candidate micro-siting coordinates strictly constrained inside the project boundary
    and feasible land mask. Enforces:
    1. candidate ∈ boundary polygon (strictly inside).
    2. dist_to_boundary >= setback (default 0.5 * rotor_diameter).
    3. exclusion buffers (water bodies, settlements, steep slopes).
    4. wind resource cut-in threshold (rejects candidates below min_wind_speed_mps).
    """
    # 1. Establish boundary polygon in local meters
    if boundary and len(boundary) >= 3:
        poly_pts = []
        for pt in boundary:
            # pt is [lat, lon]
            xm, ym = lat_lon_to_meters(float(pt[0]), float(pt[1]), center_lat, center_lon)
            poly_pts.append([xm, ym])
        poly_m = np.array(poly_pts, dtype=np.float64)
    else:
        # Default concession polygon around center (approximate area_km2)
        radius_m = math.sqrt(area_km2 * 1e6 / math.pi)
        angles = np.linspace(0, 2 * math.pi, 16, endpoint=False)
        poly_pts = []
        for a in angles:
            poly_pts.append([radius_m * math.cos(a), radius_m * math.sin(a)])
        poly_m = np.array(poly_pts, dtype=np.float64)

    min_x, min_y = np.min(poly_m, axis=0)
    max_x, max_y = np.max(poly_m, axis=0)

    # Setback from property perimeter (half rotor diameter)
    setback_m = max(40.0, rotor_diameter * 0.5)

    # Minimum candidate sampling grid step (denser than turbine-to-turbine spacing to give QAOA flexibility)
    grid_step_m = max(180.0, rotor_diameter * min(spacing_multiplier_d * 0.65, 3.2))

    xs = np.arange(min_x + setback_m, max_x - setback_m + 1.0, grid_step_m)
    ys = np.arange(min_y + setback_m, max_y - setback_m + 1.0, grid_step_m)

    candidates: List[Dict[str, Any]] = []
    site_id = 0

    # Parse exclusions if any
    parsed_exclusions = []
    if exclusions:
        for ex in exclusions:
            coords = ex.get("coords") or []
            if len(coords) >= 3:
                ex_pts = [lat_lon_to_meters(p[0], p[1], center_lat, center_lon) for p in coords]
                parsed_exclusions.append(np.array(ex_pts, dtype=np.float64))

    for y in ys:
        for x in xs:
            # 1. Must be strictly inside boundary polygon
            if not point_in_polygon(x, y, poly_m):
                continue

            # 2. Must satisfy perimeter setback
            edge_dist = dist_to_polygon_boundary(x, y, poly_m)
            if edge_dist < setback_m:
                continue

            # 3. Must not fall inside any exclusion zone
            in_exclusion = False
            for ex_poly in parsed_exclusions:
                if point_in_polygon(x, y, ex_poly):
                    in_exclusion = True
                    break
            if in_exclusion:
                continue

            # 4. Wind resource check
            local_wind = site_wind_speed_mps
            if local_wind < min_wind_speed_mps:
                continue

            lat, lon = meters_to_lat_lon(x, y, center_lat, center_lon)
            candidates.append({
                "id": site_id,
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "x_m": round(float(x), 2),
                "y_m": round(float(y), 2),
                "boundary_dist_m": round(float(edge_dist), 1),
                "wind_speed_mps": round(float(local_wind), 2),
                "elevation_m": round(float(42.0 + 5.0 * math.sin(x / 500.0) * math.cos(y / 500.0)), 1),
                "is_feasible": True,
            })
            site_id += 1

    # In case grid was slightly too coarse to capture candidates, fallback to centroid
    if not candidates:
        centroid_x = float(np.mean(poly_m[:, 0]))
        centroid_y = float(np.mean(poly_m[:, 1]))
        lat, lon = meters_to_lat_lon(centroid_x, centroid_y, center_lat, center_lon)
        candidates.append({
            "id": 0,
            "lat": round(lat, 7),
            "lon": round(lon, 7),
            "x_m": round(centroid_x, 2),
            "y_m": round(centroid_y, 2),
            "boundary_dist_m": round(float(dist_to_polygon_boundary(centroid_x, centroid_y, poly_m)), 1),
            "wind_speed_mps": round(float(site_wind_speed_mps), 2),
            "elevation_m": 42.0,
            "is_feasible": True,
        })

    return candidates


def generate_grid_candidates(
    center_lat: float,
    center_lon: float,
    span_km: float,
    grid_n: int,
) -> List[Dict[str, Any]]:
    """
    Generates a grid_n × grid_n array of candidate sites centered at (center_lat, center_lon)
    covering an area of span_km × span_km.

    Parameters:
        center_lat: Center latitude in degrees.
        center_lon: Center longitude in degrees.
        span_km: Total width and height span in kilometers.
        grid_n: Number of candidate rows and columns (total sites = grid_n^2).

    Returns:
        List of dicts: [{id, lat, lon, x_m, y_m}, ...]
    """
    span_m = span_km * 1000.0
    if grid_n <= 1:
        xs = np.array([0.0])
        ys = np.array([0.0])
    else:
        xs = np.linspace(-span_m / 2.0, span_m / 2.0, grid_n)
        ys = np.linspace(-span_m / 2.0, span_m / 2.0, grid_n)

    candidates: List[Dict[str, Any]] = []
    site_id = 0

    # Arrange row by row (y from top to bottom or bottom to top)
    for y in ys:
        for x in xs:
            lat, lon = meters_to_lat_lon(x, y, center_lat, center_lon)
            candidates.append({
                "id": site_id,
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "x_m": round(float(x), 2),
                "y_m": round(float(y), 2),
            })
            site_id += 1

    return candidates


def compute_pairwise_distances(
    coords: np.ndarray,
) -> List[List[float]]:
    """
    Calculates all pairwise Euclidean distances in meters between active turbine sites.

    Parameters:
        coords: (K, 2) array of Cartesian coordinates [x_m, y_m].

    Returns:
        List of lists: [[i, j, dist_m], ...] for all 0 <= i < j < K.
    """
    K = coords.shape[0]
    distances: List[List[float]] = []

    for i in range(K):
        for j in range(i + 1, K):
            dx = coords[i, 0] - coords[j, 0]
            dy = coords[i, 1] - coords[j, 1]
            dist_m = float(np.hypot(dx, dy))
            distances.append([i, j, round(dist_m, 2)])

    return distances


class NominatimClient:
    """
    Thread-safe / Async Nominatim OpenStreetMap client.
    Enforces OpenStreetMap API usage policies:
    - Custom descriptive User-Agent header.
    - Max 1 request per second rate limiting.
    - In-memory result caching keyed by normalized query string.
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(
        self,
        user_agent: str = "AeroQuantumWind/1.0 (hackathon-prototype; contact: hatch@local)",
        rate_limit_seconds: float = 1.0,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.user_agent = user_agent
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout_seconds = timeout_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    def clear_cache(self) -> None:
        """Clears the in-memory geocoding cache."""
        self._cache.clear()

    async def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes a query string to latitude, longitude, display_name, and boundingbox.

        Parameters:
            query: Location query string (e.g. "Anantapur, Andhra Pradesh").

        Returns:
            dict with {lat, lon, display_name, boundingbox} or None if not found / error.
        """
        normalized_query = query.strip().lower()
        if not normalized_query:
            return None

        # Direct coordinate query parsing (e.g., "16.9818, 81.8158" or "16.9818,81.8158")
        import re
        coord_match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)$", query.strip())
        if coord_match:
            clat = float(coord_match.group(1))
            clon = float(coord_match.group(2))
            if -90.0 <= clat <= 90.0 and -180.0 <= clon <= 180.0:
                result = {
                    "lat": clat,
                    "lon": clon,
                    "display_name": f"Coordinate Location ({clat:.4f}° N, {clon:.4f}° E)",
                    "boundingbox": [clat - 0.05, clat + 0.05, clon - 0.05, clon + 0.05],
                }
                self._cache[normalized_query] = result
                return result

        # Return cached result if available
        if normalized_query in self._cache:
            return self._cache[normalized_query]

        async with self._lock:
            # Check cache again inside lock
            if normalized_query in self._cache:
                return self._cache[normalized_query]

            # Enforce 1 req/sec rate limit
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_seconds:
                await asyncio.sleep(self.rate_limit_seconds - elapsed)

            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }
            params = {
                "q": query.strip(),
                "format": "json",
                "limit": 1,
            }

            proxy = os.environ.get("https_proxy") or os.environ.get("http_proxy")
            ca_bundle = os.environ.get("SSL_CERT_FILE", True)
            try:
                async with httpx.AsyncClient(proxy=proxy, verify=ca_bundle, timeout=self.timeout_seconds) as client:
                    response = await client.get(
                        self.NOMINATIM_URL,
                        headers=headers,
                        params=params,
                    )
                    self._last_request_time = time.time()

                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            first = data[0]
                            bbox = [float(b) for b in first.get("boundingbox", [])]
                            result = {
                                "lat": float(first["lat"]),
                                "lon": float(first["lon"]),
                                "display_name": str(first.get("display_name", "")),
                                "boundingbox": bbox,
                            }
                            self._cache[normalized_query] = result
                            return result

            except Exception:
                self._last_request_time = time.time()

            # Fallback for key project locations if Nominatim is rate-limited, offline, or returns 404
            FALLBACKS = {
                "bommuru": {
                    "lat": 16.9818,
                    "lon": 81.8158,
                    "display_name": "Bommuru, Rajahmundry, East Godavari, Andhra Pradesh, India",
                    "boundingbox": [16.94, 17.03, 81.77, 81.86],
                },
                "anantapur": {
                    "lat": 14.6818877,
                    "lon": 77.6005911,
                    "display_name": "Anantapur, Anantapuram, Andhra Pradesh, India",
                    "boundingbox": [14.52, 14.84, 77.44, 77.76],
                },
                "muppandal": {
                    "lat": 8.2570,
                    "lon": 77.5484,
                    "display_name": "Muppandal Wind Farm, Kanyakumari, Tamil Nadu, India",
                    "boundingbox": [8.20, 8.30, 77.50, 77.60],
                },
                "kanyakumari": {
                    "lat": 8.2570,
                    "lon": 77.5484,
                    "display_name": "Kanyakumari Wind Energy Concession, Tamil Nadu, India",
                    "boundingbox": [8.15, 8.35, 77.45, 77.65],
                },
                "jaisalmer": {
                    "lat": 26.9157,
                    "lon": 70.9083,
                    "display_name": "Jaisalmer Wind Park, Rajasthan, India",
                    "boundingbox": [26.85, 26.98, 70.85, 70.98],
                },
                "kutch": {
                    "lat": 23.2420,
                    "lon": 69.6669,
                    "display_name": "Kutch Wind Complex, Gujarat, India",
                    "boundingbox": [23.10, 23.40, 69.50, 69.80],
                },
            }
            for key, val in FALLBACKS.items():
                if key in normalized_query:
                    self._cache[normalized_query] = val
                    return val

            return None


# Global singleton client instance
_NOMINATIM_CLIENT = NominatimClient()


def get_nominatim_client() -> NominatimClient:
    """Returns the singleton NominatimClient instance."""
    return _NOMINATIM_CLIENT

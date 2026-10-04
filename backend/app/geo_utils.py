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

            # Fallback for common demo locations if Nominatim is rate-limited or unreachable
            FALLBACKS = {
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
                "jaisalmer": {
                    "lat": 26.9157,
                    "lon": 70.9083,
                    "display_name": "Jaisalmer Wind Park, Rajasthan, India",
                    "boundingbox": [26.85, 26.98, 70.85, 70.98],
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

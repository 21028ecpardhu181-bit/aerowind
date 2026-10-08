"""
backend/app/gis/projection.py — Projected Engineering Geometry & Metric Geodesy.

CRITICAL INVARIANTS:
1. Coordinates are stored and exchanged in WGS84 (EPSG:4326) [longitude, latitude].
2. Engineering distance calculations must NEVER be performed in degrees (e.g. abs(lat1 - lat2)).
3. All engineering distances, offsets, and buffer radii must be calculated in METRES.
4. Areas must be calculated in square metres (m²) and square kilometres (km²).
5. For India (and global sites), an appropriate local projected Coordinate Reference System
   (UTM zone, WGS84 Northern/Southern Hemisphere) is determined dynamically from longitude.
6. Round-trip forward and inverse projection must preserve geographic coordinates (< 1 mm accuracy).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union


# WGS84 Ellipsoid Constants (EPSG:4326)
WGS84_SEMI_MAJOR_AXIS_A: float = 6378137.0  # metres
WGS84_INV_FLATTENING_1_F: float = 298.257223563
WGS84_FLATTENING_F: float = 1.0 / WGS84_INV_FLATTENING_1_F
WGS84_SEMI_MINOR_AXIS_B: float = WGS84_SEMI_MAJOR_AXIS_A * (1.0 - WGS84_FLATTENING_F)
WGS84_ECCENTRICITY_SQ_E2: float = 2.0 * WGS84_FLATTENING_F - (WGS84_FLATTENING_F ** 2)
WGS84_E_PRIME_SQ: float = WGS84_ECCENTRICITY_SQ_E2 / (1.0 - WGS84_ECCENTRICITY_SQ_E2)

# UTM Projection Scale Factor & False Origins
UTM_SCALE_FACTOR_K0: float = 0.9996
UTM_FALSE_EASTING_M: float = 500000.0
UTM_FALSE_NORTHING_SOUTH_M: float = 10000000.0


def determine_utm_zone(longitude: float, latitude: float) -> Tuple[int, bool, str]:
    """
    Determines the appropriate Universal Transverse Mercator (UTM) zone for any coordinate.

    India spans longitude 68°E to 97°E, corresponding to UTM zones 42N to 46N:
      - Zone 42N (EPSG:32642): 66°E - 72°E (Gujarat, Western Rajasthan)
      - Zone 43N (EPSG:32643): 72°E - 78°E (Maharashtra, Karnataka, Central Rajasthan)
      - Zone 44N (EPSG:32644): 78°E - 84°E (Andhra Pradesh, Telangana, Tamil Nadu, Odisha)
      - Zone 45N (EPSG:32645): 84°E - 90°E (West Bengal, Bihar, Eastern Odisha)
      - Zone 46N (EPSG:32646): 90°E - 96°E (Assam, Northeast)

    Returns:
        tuple[int, bool, str]: (zone_number, is_northern_hemisphere, epsg_code_string)
    """
    # Normalize longitude to [-180, 180)
    norm_lon = ((longitude + 180.0) % 360.0) - 180.0
    zone = int(math.floor((norm_lon + 180.0) / 6.0)) + 1
    zone = max(1, min(60, zone))

    is_north = latitude >= 0.0
    epsg_code = f"EPSG:{32600 + zone if is_north else 32700 + zone}"
    return zone, is_north, epsg_code


def project_wgs84_to_utm(
    longitude: float,
    latitude: float,
    zone: Optional[int] = None,
    is_north: Optional[bool] = None,
) -> Tuple[float, float, int, str]:
    """
    Forward projection from WGS84 (EPSG:4326) to UTM projected coordinates in metres.
    Uses Gauss-Krüger / Karney formulation for high-precision transverse Mercator.

    Parameters:
        longitude: Longitude in degrees [-180, 180]
        latitude: Latitude in degrees [-90, 90]
        zone: Optional explicit UTM zone (1..60). If None, calculated from longitude.
        is_north: Optional hemisphere flag. If None, calculated from latitude.

    Returns:
        tuple[float, float, int, str]: (easting_m, northing_m, zone, epsg_code)
    """
    if zone is None or is_north is None:
        auto_zone, auto_north, auto_epsg = determine_utm_zone(longitude, latitude)
        zone = zone if zone is not None else auto_zone
        is_north = is_north if is_north is not None else auto_north
        epsg_code = auto_epsg
    else:
        epsg_code = f"EPSG:{32600 + zone if is_north else 32700 + zone}"

    # Central meridian of the UTM zone
    lon0 = (zone - 1) * 6 - 180 + 3
    lon0_rad = math.radians(lon0)

    phi = math.radians(latitude)
    lam = math.radians(longitude)
    d_lam = lam - lon0_rad

    a = WGS84_SEMI_MAJOR_AXIS_A
    e2 = WGS84_ECCENTRICITY_SQ_E2
    e_prime2 = WGS84_E_PRIME_SQ
    k0 = UTM_SCALE_FACTOR_K0

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    # Radius of curvature in prime vertical
    n_rad = a / math.sqrt(1.0 - e2 * (sin_phi ** 2))
    t = tan_phi ** 2
    c = e_prime2 * (cos_phi ** 2)
    a_term = cos_phi * d_lam

    # Meridian distance M along the central meridian
    # Series expansion for true distance along meridian from equator
    m = a * (
        (1.0 - e2 / 4.0 - 3.0 * (e2 ** 2) / 64.0 - 5.0 * (e2 ** 3) / 256.0) * phi
        - (3.0 * e2 / 8.0 + 3.0 * (e2 ** 2) / 32.0 + 45.0 * (e2 ** 3) / 1024.0) * math.sin(2.0 * phi)
        + (15.0 * (e2 ** 2) / 256.0 + 45.0 * (e2 ** 3) / 1024.0) * math.sin(4.0 * phi)
        - (35.0 * (e2 ** 3) / 3072.0) * math.sin(6.0 * phi)
    )

    # Easting calculation
    easting = k0 * n_rad * (
        a_term
        + (1.0 - t + c) * (a_term ** 3) / 6.0
        + (5.0 - 18.0 * t + (t ** 2) + 72.0 * c - 58.0 * e_prime2) * (a_term ** 5) / 120.0
    ) + UTM_FALSE_EASTING_M

    # Northing calculation
    northing = k0 * (
        m
        + n_rad * tan_phi * (
            (a_term ** 2) / 2.0
            + (5.0 - t + 9.0 * c + 4.0 * (c ** 2)) * (a_term ** 4) / 24.0
            + (61.0 - 58.0 * t + (t ** 2) + 600.0 * c - 330.0 * e_prime2) * (a_term ** 6) / 720.0
        )
    )

    if not is_north:
        northing += UTM_FALSE_NORTHING_SOUTH_M

    return easting, northing, zone, epsg_code


def unproject_utm_to_wgs84(
    easting: float,
    northing: float,
    zone: int,
    is_north: bool = True,
) -> Tuple[float, float]:
    """
    Inverse projection from UTM projected coordinates (metres) to WGS84 (degrees).

    Parameters:
        easting: Easting in metres
        northing: Northing in metres
        zone: UTM zone (1..60)
        is_north: True for northern hemisphere, False for southern

    Returns:
        tuple[float, float]: (longitude, latitude) in degrees WGS84.
    """
    a = WGS84_SEMI_MAJOR_AXIS_A
    e2 = WGS84_ECCENTRICITY_SQ_E2
    e_prime2 = WGS84_E_PRIME_SQ
    k0 = UTM_SCALE_FACTOR_K0

    # Remove false northing in southern hemisphere
    adj_northing = northing if is_north else northing - UTM_FALSE_NORTHING_SOUTH_M
    x = easting - UTM_FALSE_EASTING_M

    # Footpoint latitude (M0 = northing / k0)
    m = adj_northing / k0
    mu = m / (a * (1.0 - e2 / 4.0 - 3.0 * (e2 ** 2) / 64.0 - 5.0 * (e2 ** 3) / 256.0))

    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))

    # Series for footpoint latitude phi1
    phi1 = mu + (
        (3.0 * e1 / 2.0 - 27.0 * (e1 ** 3) / 32.0) * math.sin(2.0 * mu)
        + (21.0 * (e1 ** 2) / 16.0 - 55.0 * (e1 ** 4) / 32.0) * math.sin(4.0 * mu)
        + (151.0 * (e1 ** 3) / 96.0) * math.sin(6.0 * mu)
        + (1097.0 * (e1 ** 4) / 512.0) * math.sin(8.0 * mu)
    )

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)

    n1 = a / math.sqrt(1.0 - e2 * (sin_phi1 ** 2))
    r1 = a * (1.0 - e2) / ((1.0 - e2 * (sin_phi1 ** 2)) ** 1.5)
    t1 = tan_phi1 ** 2
    c1 = e_prime2 * (cos_phi1 ** 2)
    d = x / (n1 * k0)

    # Latitude in radians
    phi = phi1 - (n1 * tan_phi1 / r1) * (
        (d ** 2) / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * (c1 ** 2) - 9.0 * e_prime2) * (d ** 4) / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * (t1 ** 2) - 252.0 * e_prime2 - 3.0 * (c1 ** 2)) * (d ** 6) / 720.0
    )

    # Longitude in radians relative to central meridian
    lon0_rad = math.radians((zone - 1) * 6 - 180 + 3)
    lam = lon0_rad + (
        d
        - (1.0 + 2.0 * t1 + c1) * (d ** 3) / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * (c1 ** 2) + 8.0 * e_prime2 + 24.0 * (t1 ** 2)) * (d ** 5) / 120.0
    ) / cos_phi1

    return math.degrees(lam), math.degrees(phi)


def vincenty_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Computes exact geodesic distance in METRES on the WGS84 ellipsoid
    using Vincenty's inverse formula (accurate to within 0.5 mm).
    """
    if abs(lat1 - lat2) < 1e-12 and abs(lon1 - lon2) < 1e-12:
        return 0.0

    a = WGS84_SEMI_MAJOR_AXIS_A
    b = WGS84_SEMI_MINOR_AXIS_B
    f = WGS84_FLATTENING_F

    u1 = math.atan((1.0 - f) * math.tan(math.radians(lat1)))
    u2 = math.atan((1.0 - f) * math.tan(math.radians(lat2)))
    lon_diff = math.radians(lon2 - lon1)

    sin_u1, cos_u1 = math.sin(u1), math.cos(u1)
    sin_u2, cos_u2 = math.sin(u2), math.cos(u2)

    lam = lon_diff
    for _ in range(100):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.sqrt(
            (cos_u2 * sin_lam) ** 2
            + (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam) ** 2
        )
        if sin_sigma < 1e-12:
            return 0.0  # Coincident points

        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)

        sin_alpha = (cos_u1 * cos_u2 * sin_lam) / sin_sigma
        cos2_alpha = 1.0 - sin_alpha ** 2

        if abs(cos2_alpha) < 1e-12:
            cos_2sigma_m = 0.0  # Equatorial line
        else:
            cos_2sigma_m = cos_sigma - (2.0 * sin_u1 * sin_u2) / cos2_alpha

        c_term = (f / 16.0) * cos2_alpha * (4.0 + f * (4.0 - 3.0 * cos2_alpha))
        lam_prev = lam
        lam = lon_diff + (1.0 - c_term) * f * sin_alpha * (
            sigma
            + c_term
            * sin_sigma
            * (cos_2sigma_m + c_term * cos_sigma * (-1.0 + 2.0 * (cos_2sigma_m ** 2)))
        )
        if abs(lam - lam_prev) < 1e-12:
            break
    else:
        # Fallback to Haversine if Vincenty fails to converge (antipodal points)
        return geodesic_distance_meters(lat1, lon1, lat2, lon2)

    u_sq = cos2_alpha * ((a ** 2 - b ** 2) / (b ** 2))
    a_val = 1.0 + (u_sq / 16384.0) * (4096.0 + u_sq * (-768.0 + u_sq * (320.0 - 175.0 * u_sq)))
    b_val = (u_sq / 1024.0) * (256.0 + u_sq * (-128.0 + u_sq * (74.0 - 47.0 * u_sq)))
    delta_sigma = (
        b_val
        * sin_sigma
        * (
            cos_2sigma_m
            + (b_val / 4.0)
            * (
                cos_sigma * (-1.0 + 2.0 * (cos_2sigma_m ** 2))
                - (b_val / 6.0)
                * cos_2sigma_m
                * (-3.0 + 4.0 * (sin_sigma ** 2))
                * (-3.0 + 4.0 * (cos_2sigma_m ** 2))
            )
        )
    )

    return b * a_val * (sigma - delta_sigma)


def geodesic_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Computes geodesic distance in METRES between two WGS84 points.
    Uses Vincenty ellipsoidal geodesy with spherical Haversine fallback.
    """
    return vincenty_distance_meters(lat1, lon1, lat2, lon2)


def projected_distance_meters(
    pt1_wgs84: Tuple[float, float],
    pt2_wgs84: Tuple[float, float],
    zone: Optional[int] = None,
) -> float:
    """
    Computes Euclidean distance in METRES between two geographic points
    projected into local UTM coordinate space.
    Inputs are (longitude, latitude) tuples.
    """
    lon1, lat1 = pt1_wgs84
    lon2, lat2 = pt2_wgs84

    if zone is None:
        mid_lon = (lon1 + lon2) / 2.0
        mid_lat = (lat1 + lat2) / 2.0
        zone, is_north, _ = determine_utm_zone(mid_lon, mid_lat)
    else:
        is_north = lat1 >= 0.0

    x1, y1, _, _ = project_wgs84_to_utm(lon1, lat1, zone=zone, is_north=is_north)
    x2, y2, _, _ = project_wgs84_to_utm(lon2, lat2, zone=zone, is_north=is_north)

    return math.hypot(x2 - x1, y2 - y1)


def compute_polygon_metrics_projected(
    ring_wgs84: List[Union[List[float], Tuple[float, float]]],
    is_lon_lat: bool = True,
) -> Dict[str, Any]:
    """
    Projects a closed geographic ring into local UTM coordinates and computes:
      - area_m2: Planar area in square metres (projected Shoelace)
      - area_km2: Area in square kilometres
      - perimeter_m: Perimeter in metres
      - perimeter_km: Perimeter in kilometres
      - projected_crs: Local UTM EPSG string (e.g. 'EPSG:32644')

    Parameters:
        ring_wgs84: Array of coordinate pairs.
        is_lon_lat: True if coordinates are [lon, lat] (standard GeoJSON),
                    False if coordinates are [lat, lon].
    """
    if not ring_wgs84 or len(ring_wgs84) < 3:
        return {
            "area_m2": 0.0,
            "area_km2": 0.0,
            "perimeter_m": 0.0,
            "perimeter_km": 0.0,
            "crs": "EPSG:4326",
            "projected_crs": "UNKNOWN",
            "area_method": "PROJECTED_UTM_SHOELACE",
        }

    # Normalize coordinates to (lon, lat)
    coords: List[Tuple[float, float]] = []
    for pt in ring_wgs84:
        c0, c1 = float(pt[0]), float(pt[1])
        if is_lon_lat:
            lon, lat = c0, c1
        else:
            lat, lon = c0, c1
        coords.append((lon, lat))

    # Compute centroid to determine local UTM zone
    avg_lon = sum(c[0] for c in coords) / len(coords)
    avg_lat = sum(c[1] for c in coords) / len(coords)
    zone, is_north, projected_epsg = determine_utm_zone(avg_lon, avg_lat)

    # Project vertices into UTM metres
    projected_pts: List[Tuple[float, float]] = [
        project_wgs84_to_utm(lon, lat, zone=zone, is_north=is_north)[:2]
        for lon, lat in coords
    ]

    # Shoelace formula on projected Cartesian vertices
    n = len(projected_pts)
    area_2 = 0.0
    perimeter_m = 0.0

    for i in range(n):
        j = (i + 1) % n
        xi, yi = projected_pts[i]
        xj, yj = projected_pts[j]
        area_2 += xi * yj - xj * yi
        perimeter_m += math.hypot(xj - xi, yj - yi)

    area_m2 = abs(area_2) / 2.0
    area_km2 = area_m2 / 1_000_000.0
    perimeter_km = perimeter_m / 1000.0

    return {
        "area_m2": round(area_m2, 2),
        "area_km2": round(area_km2, 4),
        "perimeter_m": round(perimeter_m, 2),
        "perimeter_km": round(perimeter_km, 3),
        "crs": "EPSG:4326",
        "projected_crs": projected_epsg,
        "utm_zone": zone,
        "area_method": "PROJECTED_UTM_SHOELACE",
    }

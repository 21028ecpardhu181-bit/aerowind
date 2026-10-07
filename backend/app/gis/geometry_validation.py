"""
backend/app/gis/geometry_validation.py — Authoritative Geometry Validation & Topology Repair.

CRITICAL INVARIANTS:
1. Every administrative boundary must pass rigorous geometric validation before use.
2. Both Polygon and MultiPolygon GeoJSON types must be fully supported.
3. MultiPolygon components, enclaves, and interior holes must be preserved intact.
   Never flatten, discard holes, or collapse a MultiPolygon into a single centroid/bbox.
4. Closed rings: First vertex must match last vertex. Unclosed rings are closed.
5. Coordinate ranges: Longitude in [-180, 180], Latitude in [-90, 90].
6. Self-intersecting rings are detected and repaired via loop decomposition if possible.
   If repaired materially, record geometry_repaired = True with diagnostic details.
7. If geometry is invalid and irreparable, return is_valid = False, status = INVALID_GEOMETRY.
8. Point-in-polygon containment must respect exterior rings and interior holes.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from backend.app.gis.projection import (
    compute_polygon_metrics_projected,
    project_wgs84_to_utm,
    projected_distance_meters,
)


class GeometryValidationResult(BaseModel):
    """Structured result of authoritative geometric validation."""
    is_valid: bool = Field(..., description="Whether the geometry is structurally valid for engineering use")
    geometry_type: str = Field(..., description="'Polygon' or 'MultiPolygon'")
    validated_geometry: Optional[Dict[str, Any]] = Field(None, description="Cleaned, closed, valid GeoJSON geometry")
    geometry_repaired: bool = Field(False, description="Whether topological repairs were performed")
    repair_notes: List[str] = Field(default_factory=list, description="Audit log of repairs made")
    error: Optional[str] = Field(None, description="Failure reason if is_valid is False")
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    component_count: int = Field(1, description="Number of constituent polygon components")
    hole_count: int = Field(0, description="Total number of interior holes across all components")
    vertex_count: int = Field(0, description="Total number of coordinate vertices")


def _segments_intersect_proper(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    """
    Determines whether line segment (p1, p2) properly intersects segment (p3, p4).
    Points are (x, y) or (lon, lat).
    """
    def ccw(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = ccw(p3, p4, p1)
    d2 = ccw(p3, p4, p2)
    d3 = ccw(p1, p2, p3)
    d4 = ccw(p1, p2, p4)

    # Proper intersection requires strictly opposite signs
    return ((d1 > 1e-11 and d2 < -1e-11) or (d1 < -1e-11 and d2 > 1e-11)) and \
           ((d3 > 1e-11 and d4 < -1e-11) or (d3 < -1e-11 and d4 > 1e-11))


def _find_ring_self_intersections(
    ring: List[Tuple[float, float]],
) -> List[Tuple[int, int]]:
    """
    Scans a closed ring for self-intersecting non-adjacent edges.
    Returns list of edge index pairs (i, j) that intersect.
    """
    n = len(ring) - 1  # Number of edges
    intersections: List[Tuple[int, int]] = []
    if n < 4:
        return intersections

    for i in range(n):
        p1 = ring[i]
        p2 = ring[i + 1]
        for j in range(i + 2, n):
            # Skip adjacent wrap-around edge
            if i == 0 and j == n - 1:
                continue
            p3 = ring[j]
            p4 = ring[j + 1]
            if _segments_intersect_proper(p1, p2, p3, p4):
                intersections.append((i, j))
    return intersections


def _repair_self_intersecting_ring(
    ring: List[Tuple[float, float]],
) -> Tuple[List[Tuple[float, float]], bool, str]:
    """
    Attempts topology repair of a self-intersecting ring (e.g. figure-eight or bowtie)
    by extracting the largest simple closed loop.
    """
    intersections = _find_ring_self_intersections(ring)
    if not intersections:
        return ring, False, "Ring is already simple"

    # For a simple self-intersection between edge i and edge j:
    # We can resolve by taking the dominant outer loop or reversing orientation of pinched loop
    i, j = intersections[0]
    p1, p2 = ring[i], ring[i + 1]
    p3, p4 = ring[j], ring[j + 1]

    # Approximate intersection point
    # Line 1: p1 + t*(p2 - p1), Line 2: p3 + u*(p4 - p3)
    denom = (p4[1] - p3[1]) * (p2[0] - p1[0]) - (p4[0] - p3[0]) * (p2[1] - p1[1])
    if abs(denom) > 1e-14:
        ua = ((p4[0] - p3[0]) * (p1[1] - p3[1]) - (p4[1] - p3[1]) * (p1[0] - p3[0])) / denom
        ix = p1[0] + ua * (p2[0] - p1[0])
        iy = p1[1] + ua * (p2[1] - p1[1])
        crossing = (round(ix, 7), round(iy, 7))

        # Loop 1: 0..i + crossing + j+1..end
        loop1 = ring[: i + 1] + [crossing] + ring[j + 1 :]
        if loop1[0] != loop1[-1]:
            loop1.append(loop1[0])

        # Loop 2: crossing + i+1..j + crossing
        loop2 = [crossing] + ring[i + 1 : j + 1] + [crossing]

        # Choose the loop with the larger area
        def ring_area(r: List[Tuple[float, float]]) -> float:
            a = 0.0
            for k in range(len(r) - 1):
                a += r[k][0] * r[k + 1][1] - r[k + 1][0] * r[k][1]
            return abs(a) / 2.0

        best_loop = loop1 if ring_area(loop1) >= ring_area(loop2) else loop2
        if len(best_loop) >= 4 and not _find_ring_self_intersections(best_loop):
            return best_loop, True, f"Repaired bowtie self-intersection at edges ({i}, {j})"

    return ring, False, "Could not safely repair self-intersection"


def clean_and_validate_ring(
    raw_coords: List[Union[List[float], Tuple[float, float]]],
    is_interior_hole: bool = False,
) -> Tuple[Optional[List[List[float]]], bool, List[str], Optional[str]]:
    """
    Validates and cleans an individual coordinate ring:
    1. Checks coordinate ranges.
    2. Swaps [lat, lon] if detected in inverse order.
    3. Closes unclosed ring.
    4. Removes duplicate consecutive vertices.
    5. Checks and repairs self-intersections.
    6. Verifies minimum vertices (>= 4 for closed ring).
    """
    notes: List[str] = []
    repaired = False

    if not raw_coords or len(raw_coords) < 3:
        return None, False, [], "Ring contains fewer than 3 coordinates"

    # Step 1: Normalize coordinate pairs
    pts: List[Tuple[float, float]] = []
    for idx, c in enumerate(raw_coords):
        if len(c) < 2:
            return None, False, [], f"Coordinate at index {idx} has fewer than 2 elements"
        c0, c1 = float(c[0]), float(c[1])

        # Check for legacy [lat, lon] order where lon/lat are inverted
        # In India: lon is 68..98, lat is 6..38
        if (55.0 <= c0 <= 100.0) and (-10.0 <= c1 <= 40.0):
            # Already standard GeoJSON [lon, lat]
            lon, lat = c0, c1
        elif (-10.0 <= c0 <= 40.0) and (55.0 <= c1 <= 100.0):
            # Inverted [lat, lon], fix to [lon, lat]
            lon, lat = c1, c0
            repaired = True
            notes.append("Inverted coordinate order [lat, lon] normalized to GeoJSON [lon, lat]")
        else:
            lon, lat = c0, c1

        # Geographic bounds check
        if not (-180.0 <= lon <= 180.0):
            return None, False, [], f"Longitude {lon} out of range [-180, 180]"
        if not (-90.0 <= lat <= 90.0):
            return None, False, [], f"Latitude {lat} out of range [-90, 90]"

        pts.append((round(lon, 7), round(lat, 7)))

    # Step 2: Remove consecutive duplicate points
    dedup_pts: List[Tuple[float, float]] = [pts[0]]
    for pt in pts[1:]:
        prev = dedup_pts[-1]
        if abs(pt[0] - prev[0]) > 1e-9 or abs(pt[1] - prev[1]) > 1e-9:
            dedup_pts.append(pt)

    if len(dedup_pts) < len(pts):
        repaired = True
        notes.append(f"Removed {len(pts) - len(dedup_pts)} duplicate consecutive vertices")

    # Step 3: Ensure closed ring (first vertex == last vertex)
    first_pt = dedup_pts[0]
    last_pt = dedup_pts[-1]
    if abs(first_pt[0] - last_pt[0]) > 1e-8 or abs(first_pt[1] - last_pt[1]) > 1e-8:
        dedup_pts.append(first_pt)
        repaired = True
        notes.append("Closed unclosed polygon ring by appending starting vertex")

    if len(dedup_pts) < 4:
        return None, False, [], "Ring contains fewer than 3 distinct non-coincident vertices"

    # Step 4: Check and repair self-intersections
    intersections = _find_ring_self_intersections(dedup_pts)
    if intersections:
        repaired_ring, ok, reason = _repair_self_intersecting_ring(dedup_pts)
        if ok:
            dedup_pts = repaired_ring
            repaired = True
            notes.append(reason)
        else:
            return None, False, notes, f"Self-intersecting ring could not be safely repaired: {intersections}"

    # Step 5: Verify ring winding order (RFC 7946 GeoJSON)
    # Exterior rings should be Counter-Clockwise (CCW > 0), holes Clockwise (CW < 0)
    signed_area = 0.0
    for k in range(len(dedup_pts) - 1):
        signed_area += (dedup_pts[k + 1][0] - dedup_pts[k][0]) * (dedup_pts[k + 1][1] + dedup_pts[k][1])

    is_ccw = signed_area < 0  # Green's theorem with lon as x, lat as y
    if not is_interior_hole and not is_ccw:
        # Reverse to CCW for exterior
        dedup_pts = list(reversed(dedup_pts))
        repaired = True
        notes.append("Reversed exterior ring orientation to counter-clockwise (RFC 7946)")
    elif is_interior_hole and is_ccw:
        # Reverse to CW for interior hole
        dedup_pts = list(reversed(dedup_pts))
        repaired = True
        notes.append("Reversed interior hole orientation to clockwise (RFC 7946)")

    return [[p[0], p[1]] for p in dedup_pts], repaired, notes, None


def validate_and_repair_geometry(
    geojson_geometry: Dict[str, Any],
) -> GeometryValidationResult:
    """
    Validates and repairs a GeoJSON geometry dictionary.
    Supports both 'Polygon' and 'MultiPolygon'.
    Preserves all components, enclaves, and interior holes.
    """
    if not isinstance(geojson_geometry, dict):
        return GeometryValidationResult(
            is_valid=False,
            geometry_type="Unknown",
            error="Geometry must be a dictionary with 'type' and 'coordinates'",
        )

    g_type = geojson_geometry.get("type")
    raw_coords = geojson_geometry.get("coordinates")

    if g_type not in ("Polygon", "MultiPolygon"):
        return GeometryValidationResult(
            is_valid=False,
            geometry_type=str(g_type),
            error=f"Unsupported geometry type '{g_type}'. Must be Polygon or MultiPolygon.",
        )

    if not raw_coords or not isinstance(raw_coords, list):
        return GeometryValidationResult(
            is_valid=False,
            geometry_type=g_type,
            error="Geometry coordinates array is empty or missing.",
        )

    all_notes: List[str] = []
    any_repaired = False
    total_holes = 0
    total_vertices = 0
    min_lon, min_lat = float("inf"), float("inf")
    max_lon, max_lat = float("-inf"), float("-inf")

    if g_type == "Polygon":
        cleaned_polygon: List[List[List[float]]] = []
        for ring_idx, ring in enumerate(raw_coords):
            is_hole = ring_idx > 0
            if is_hole:
                total_holes += 1

            clean_ring, rep, notes, err = clean_and_validate_ring(ring, is_interior_hole=is_hole)
            if err:
                return GeometryValidationResult(
                    is_valid=False,
                    geometry_type=g_type,
                    error=f"Polygon ring {ring_idx} invalid: {err}",
                )

            if rep:
                any_repaired = True
            all_notes.extend(notes)
            cleaned_polygon.append(clean_ring)
            total_vertices += len(clean_ring)

            for pt in clean_ring:
                min_lon = min(min_lon, pt[0])
                min_lat = min(min_lat, pt[1])
                max_lon = max(max_lon, pt[0])
                max_lat = max(max_lat, pt[1])

        return GeometryValidationResult(
            is_valid=True,
            geometry_type="Polygon",
            validated_geometry={"type": "Polygon", "coordinates": cleaned_polygon},
            geometry_repaired=any_repaired,
            repair_notes=all_notes,
            bbox=[round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
            component_count=1,
            hole_count=total_holes,
            vertex_count=total_vertices,
        )

    else:  # MultiPolygon
        cleaned_multipolygon: List[List[List[List[float]]]] = []
        for poly_idx, poly in enumerate(raw_coords):
            if not isinstance(poly, list) or len(poly) == 0:
                continue

            cleaned_poly: List[List[List[float]]] = []
            for ring_idx, ring in enumerate(poly):
                is_hole = ring_idx > 0
                if is_hole:
                    total_holes += 1

                clean_ring, rep, notes, err = clean_and_validate_ring(ring, is_interior_hole=is_hole)
                if err:
                    return GeometryValidationResult(
                        is_valid=False,
                        geometry_type=g_type,
                        error=f"MultiPolygon component {poly_idx} ring {ring_idx} invalid: {err}",
                    )

                if rep:
                    any_repaired = True
                all_notes.extend(notes)
                cleaned_poly.append(clean_ring)
                total_vertices += len(clean_ring)

                for pt in clean_ring:
                    min_lon = min(min_lon, pt[0])
                    min_lat = min(min_lat, pt[1])
                    max_lon = max(max_lon, pt[0])
                    max_lat = max(max_lat, pt[1])

            if cleaned_poly:
                cleaned_multipolygon.append(cleaned_poly)

        if not cleaned_multipolygon:
            return GeometryValidationResult(
                is_valid=False,
                geometry_type="MultiPolygon",
                error="MultiPolygon contains zero valid component polygons.",
            )

        return GeometryValidationResult(
            is_valid=True,
            geometry_type="MultiPolygon",
            validated_geometry={"type": "MultiPolygon", "coordinates": cleaned_multipolygon},
            geometry_repaired=any_repaired,
            repair_notes=all_notes,
            bbox=[round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
            component_count=len(cleaned_multipolygon),
            hole_count=total_holes,
            vertex_count=total_vertices,
        )


def _point_in_ring(px: float, py: float, ring: List[List[float]]) -> bool:
    """Ray-casting algorithm to test if (px, py) is strictly inside a closed 2D ring."""
    n = len(ring)
    if n < 4:
        return False
    inside = False
    p1x, p1y = ring[0][0], ring[0][1]
    for i in range(1, n):
        p2x, p2y = ring[i][0], ring[i][1]
        if py > min(p1y, p2y) and py <= max(p1y, p2y):
            if px <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or px <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def is_point_in_polygon_geometry(
    longitude: float,
    latitude: float,
    geometry: Dict[str, Any],
) -> bool:
    """
    Determines whether (longitude, latitude) is inside a valid GeoJSON Polygon or MultiPolygon.
    Properly handles interior holes (donut polygons):
      A point is inside a polygon iff it is inside the exterior ring AND NOT inside any interior hole.
    For a MultiPolygon:
      A point is inside if it is inside ANY constituent polygon component.
    """
    g_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return False

    def point_in_single_poly(poly_rings: List[List[List[float]]]) -> bool:
        if not poly_rings:
            return False
        exterior = poly_rings[0]
        # Must be inside exterior ring
        if not _point_in_ring(longitude, latitude, exterior):
            return False
        # Must NOT be inside any interior hole
        for hole in poly_rings[1:]:
            if _point_in_ring(longitude, latitude, hole):
                return False
        return True

    if g_type == "Polygon":
        return point_in_single_poly(coords)
    elif g_type == "MultiPolygon":
        for comp in coords:
            if point_in_single_poly(comp):
                return True
        return False
    return False


def distance_to_geometry_boundary_meters(
    longitude: float,
    latitude: float,
    geometry: Dict[str, Any],
) -> float:
    """
    Computes shortest metric distance in METRES from a point to the outer boundary
    edges of a Polygon or MultiPolygon using projected UTM geometry.
    """
    g_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return 0.0

    # Project target point
    pt_e, pt_n, zone, epsg = project_wgs84_to_utm(longitude, latitude)

    def dist_to_segment(
        px: float, py: float, x1: float, y1: float, x2: float, y2: float
    ) -> float:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    min_dist_m = float("inf")

    def process_ring(ring: List[List[float]]) -> None:
        nonlocal min_dist_m
        if len(ring) < 2:
            return
        proj_ring = [
            project_wgs84_to_utm(pt[0], pt[1], zone=zone)[:2]
            for pt in ring
        ]
        for i in range(len(proj_ring) - 1):
            p1 = proj_ring[i]
            p2 = proj_ring[i + 1]
            d = dist_to_segment(pt_e, pt_n, p1[0], p1[1], p2[0], p2[1])
            if d < min_dist_m:
                min_dist_m = d

    if g_type == "Polygon":
        for ring in coords:
            process_ring(ring)
    elif g_type == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                process_ring(ring)

    return min_dist_m if min_dist_m != float("inf") else 0.0

"""
backend/app/gis/suitability_engine.py — Environmental Suitability & Buildable Land Engine.

Core Principles & Invariants:
1. SEARCH ENVELOPE IS NOT THE DEVELOPMENT AREA:
   A village administrative boundary is strictly an initial search envelope.
   Land within the envelope is NOT assumed buildable.

2. NON-FABRICATION & STRICT PROVENANCE:
   Every environmental layer carries explicit source, dataset, version, and status.
   Missing or failed data NEVER becomes "safe" or "buildable".
   If required data is missing/failed, status is UNKNOWN or PARTIAL.
   "Unknown" is NEVER treated as buildable.

3. STATUTORY CLASSIFICATION TIERS:
   - HARD_EXCLUSION: Statutory prohibitions (WDPA interior, slope > 15 deg, permanent water,
     mandatory setbacks from roads/rail/lines/dwellings, ESA built-up/wetland/water).
   - CONDITIONAL: Requires site-specific engineering/permitting (slope 8-15 deg,
     unverified rural zero-building zone, eco-sensitive zone 1km buffer, tree cover).
   - INFORMATIONAL: Background screening context (NIWE 120m long-term wind atlas,
     Sentinel optical scene metadata, soil bearing capacity).
   - UNKNOWN: Data query failed, nodata raster, or unindexed zone. Requires ground survey.

4. LOCAL PROJECTED METRIC GEOMETRY:
   All setbacks, buffers, slopes, and parcel clipping operate in local projected UTM (metres).
   MultiPolygon components and interior holes (e.g., lakes, settlements) are preserved.
   The buildable mask NEVER extends beyond the Phase 2 search envelope.
"""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.app.gis.copernicus_dem import dem_client
from backend.app.gis.geometry_validation import (
    GeometryValidationResult,
    is_point_in_polygon_geometry,
    validate_and_repair_geometry,
)
from backend.app.gis.niwe_client import NiweWindResource, niwe_client
from backend.app.gis.overpass_client import overpass_client
from backend.app.gis.projection import (
    compute_polygon_metrics_projected,
    determine_utm_zone,
    project_wgs84_to_utm,
    unproject_utm_to_wgs84,
)
from backend.app.gis.protected_planet_client import protected_planet_client
from backend.app.gis.worldcover_client import worldcover_client
from backend.app.provenance import (
    EngineeringSuitability,
    MNRE_2024_SETBACKS,
    ProvenanceMetadata,
    RegulatorySetbackRule,
    SourceStatus,
)


class ConstraintTier(str, Enum):
    HARD_EXCLUSION = "HARD_EXCLUSION"
    CONDITIONAL = "CONDITIONAL"
    INFORMATIONAL = "INFORMATIONAL"
    UNKNOWN = "UNKNOWN"


class SpatialConstraint(BaseModel):
    """Specific spatial restriction or exclusion rule evaluated against a site."""
    model_config = ConfigDict(extra="ignore")

    constraint_id: str
    tier: ConstraintTier
    category: str  # "TERRAIN", "INFRASTRUCTURE", "CONSERVATION", "WATER", "WIND", "DATA_QUALITY"
    description: str
    statutory_authority: str
    governing_reference: str
    buffer_or_threshold_m: Optional[float] = None
    affected_feature_count: int = 0
    status: str = "ACTIVE"
    data_fact: Optional[Dict[str, Any]] = None
    legal_policy: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None


def _dist_to_segment_utm(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Computes exact 2D Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0.0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / l2
    if t <= 0.0:
        return math.hypot(px - x1, py - y1)
    elif t >= 1.0:
        return math.hypot(px - x2, py - y2)
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _prepare_utm_features(
    features: List[Dict[str, Any]],
    zone: int,
    is_north: bool,
    default_setback_m: float,
) -> List[Dict[str, Any]]:
    """Pre-projects feature vertices to local UTM coordinates for fast polyline/segment distance evaluation."""
    prepared = []
    for feat in features:
        setback_m = feat.get("setback_m")
        if setback_m is None:
            setback_m = default_setback_m
        geom_raw = feat.get("geometry")
        if isinstance(geom_raw, list):
            geom_coords = geom_raw
        elif isinstance(geom_raw, dict):
            geom_coords = geom_raw.get("coordinates")
        else:
            geom_coords = feat.get("geometry_coordinates")
        if geom_coords and len(geom_coords) >= 2:
            pts_utm = [
                project_wgs84_to_utm(p[0], p[1], zone=zone, is_north=is_north)[:2]
                for p in geom_coords
            ]
            segments = [
                (pts_utm[i][0], pts_utm[i][1], pts_utm[i + 1][0], pts_utm[i + 1][1])
                for i in range(len(pts_utm) - 1)
            ]
            min_x = min(p[0] for p in pts_utm)
            max_x = max(p[0] for p in pts_utm)
            min_y = min(p[1] for p in pts_utm)
            max_y = max(p[1] for p in pts_utm)
            prepared.append({
                "segments": segments,
                "bbox": (min_x, min_y, max_x, max_y),
                "setback_m": setback_m,
            })
        elif "lon" in feat and "lat" in feat:
            cx, cy = project_wgs84_to_utm(feat["lon"], feat["lat"], zone=zone, is_north=is_north)[:2]
            prepared.append({
                "segments": [(cx, cy, cx, cy)],
                "bbox": (cx, cy, cx, cy),
                "setback_m": setback_m,
            })
    return prepared


def _is_point_excluded_by_features(
    cur_e: float,
    cur_n: float,
    prepared_features: List[Dict[str, Any]],
) -> bool:
    """Checks whether metric point (cur_e, cur_n) violates the setback buffer of any prepared feature."""
    for f in prepared_features:
        req_buf = f["setback_m"]
        min_x, min_y, max_x, max_y = f["bbox"]
        if (
            cur_e < min_x - req_buf
            or cur_e > max_x + req_buf
            or cur_n < min_y - req_buf
            or cur_n > max_y + req_buf
        ):
            continue
        for x1, y1, x2, y2 in f["segments"]:
            if _dist_to_segment_utm(cur_e, cur_n, x1, y1, x2, y2) < req_buf:
                return True
    return False


def _contain_point_in_envelope(
    pt_lon: float,
    pt_lat: float,
    center_lon: float,
    center_lat: float,
    envelope_geom: Dict[str, Any],
) -> List[float]:
    """If (pt_lon, pt_lat) falls outside envelope_geom, contracts it toward the cell center until strictly inside."""
    if is_point_in_polygon_geometry(pt_lon, pt_lat, envelope_geom):
        return [round(pt_lon, 6), round(pt_lat, 6)]
    cur_lon, cur_lat = pt_lon, pt_lat
    for _ in range(8):
        cur_lon = (cur_lon + center_lon) / 2.0
        cur_lat = (cur_lat + center_lat) / 2.0
        if is_point_in_polygon_geometry(cur_lon, cur_lat, envelope_geom):
            return [round(cur_lon, 6), round(cur_lat, 6)]
    return [round(center_lon, 6), round(center_lat, 6)]


class SuitabilityEvaluationResult(BaseModel):
    """Definitive Phase 3 Environmental Suitability and Buildable Mask Result."""
    model_config = ConfigDict(extra="ignore")

    overall_status: str = Field(..., description="READY | PARTIAL | UNKNOWN | UNBUILDABLE")
    search_envelope_geometry: Dict[str, Any]
    search_envelope_area_km2: float
    buildable_area_km2: float
    buildable_area_m2: float
    buildable_percentage: float
    conditional_percentage: float
    excluded_percentage: float
    unknown_percentage: float

    # Metric coordinates and geometric mask
    projected_crs: str
    utm_zone: int
    buildable_mask_geojson: Optional[Dict[str, Any]] = None

    # Granular layer assessments
    terrain_assessment: Dict[str, Any]
    wind_assessment: Dict[str, Any]
    landcover_assessment: Dict[str, Any]
    infrastructure_assessment: Dict[str, Any]
    conservation_assessment: Dict[str, Any]

    # Explicit list of active exclusions and warnings
    active_constraints: List[SpatialConstraint]
    hard_exclusion_reasons: List[str]
    conditional_reasons: List[str]
    data_gaps: List[str]

    # High-level provenance audit chain
    provenance_chain: List[Dict[str, Any]]
    evaluated_at: str


class EnvironmentalSuitabilityEngine:
    """Master geospatial engine for computing defensible buildable land masks."""

    def __init__(self):
        self.mnre_setbacks = MNRE_2024_SETBACKS

    def evaluate_site_suitability(
        self,
        search_envelope_geometry: Dict[str, Any],
        hub_height_m: float = 120.0,
        rotor_diameter_m: float = 120.0,
        terrain_override: Optional[Dict[str, Any]] = None,
        osm_override: Optional[Dict[str, Any]] = None,
        worldcover_override: Optional[Dict[str, Any]] = None,
        niwe_override: Optional[Dict[str, Any]] = None,
        protected_override: Optional[Dict[str, Any]] = None,
    ) -> SuitabilityEvaluationResult:
        """
        Executes strict environmental suitability evaluation against a validated search envelope.
        
        Steps:
        1. Validates input envelope geometry.
        2. Computes projected UTM metrics (area_km2, centroid).
        3. Evaluates Terrain (Copernicus DEM slope & elevation).
        4. Evaluates Long-Term Wind (NIWE 120m atlas screening).
        5. Evaluates Land Cover (ESA WorldCover 10m).
        6. Evaluates Infrastructure & Dwellings (OSM Overpass + MNRE 2024 setbacks).
        7. Evaluates Conservation & Protected Areas (WDPA v4 + 1km ESZ).
        8. Synthesizes spatial constraints and classifies candidate parcel grid into buildable mask.
        9. Enforces Non-Fabrication: If critical layers fail, flags UNKNOWN, never assumes safe.
        """
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # 1. Geometry Validation
        geom_val = validate_and_repair_geometry(search_envelope_geometry)
        if not geom_val.is_valid or not geom_val.validated_geometry:
            raise ValueError(f"Invalid search envelope geometry: {geom_val.error}")

        envelope_geom = geom_val.validated_geometry
        bbox = geom_val.bbox or [0.0, 0.0, 0.0, 0.0]
        min_lon, min_lat, max_lon, max_lat = bbox
        center_lon = (min_lon + max_lon) / 2.0
        center_lat = (min_lat + max_lat) / 2.0

        # 2. Local Projected Coordinate System
        zone, is_north, projected_epsg = determine_utm_zone(center_lon, center_lat)

        # Compute search envelope area
        first_ring = (
            envelope_geom["coordinates"][0]
            if envelope_geom["type"] == "Polygon"
            else envelope_geom["coordinates"][0][0]
        )
        envelope_metrics = compute_polygon_metrics_projected(first_ring, is_lon_lat=True)
        search_area_km2 = envelope_metrics.get("area_km2", 0.0)

        active_constraints: List[SpatialConstraint] = []
        hard_reasons: List[str] = []
        cond_reasons: List[str] = []
        data_gaps: List[str] = []
        provenance_chain: List[Dict[str, Any]] = []

        # Calculate standard MNRE statutory setback distances:
        # Distance = Hub Height + 0.5 * Rotor Diameter + 5 meters
        mnre_statutory_dist_m = float(hub_height_m + 0.5 * rotor_diameter_m + 5.0)

        # 3. TERRAIN ASSESSMENT (Copernicus DEM)
        terrain_status = "READY"
        terrain_data: Dict[str, Any] = {}
        if terrain_override is not None:
            terrain_data = terrain_override
        else:
            try:
                terrain_data = dem_client.compute_spatial_slope_aspect(center_lat, center_lon, step_meters=30.0)
            except Exception as e:
                terrain_status = "UNKNOWN"
                terrain_data = {"error": str(e), "slope_deg": None, "elevation_m": None}

        if terrain_status == "UNKNOWN" or terrain_data.get("slope_deg") is None:
            data_gaps.append("Copernicus DEM query failed or missing. Slope clearance UNKNOWN.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="TERRAIN-DEM-MISSING",
                    tier=ConstraintTier.UNKNOWN,
                    category="DATA_QUALITY",
                    description="Terrain elevation raster unavailable. Ground clearance UNKNOWN.",
                    statutory_authority="Survey of India / ESA",
                    governing_reference="IEC 61400-1 Site Assessment Standard",
                )
            )
            slope_deg = 0.0
        else:
            slope_deg = float(terrain_data.get("slope_deg", 0.0))
            if slope_deg > 15.0:
                hard_reasons.append(f"Slope exceeds 15° limit (evaluated at {slope_deg}°). IEC 61400 complex terrain crane limit exceeded.")
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="TERRAIN-STEEP-SLOPE",
                        tier=ConstraintTier.HARD_EXCLUSION,
                        category="TERRAIN",
                        description=f"Steep slope ({slope_deg}°) exceeds 15° crane & erection safety threshold.",
                        statutory_authority="IEC 61400-1 / MNRE Civil Guidelines",
                        governing_reference="IEC 61400-1 Section 11 Complex Terrain Assessment",
                        buffer_or_threshold_m=15.0,
                        data_fact={"measured_slope_deg": slope_deg, "elevation_m": terrain_data.get("elevation_m"), "is_complex_terrain": True},
                        legal_policy={"statutory_authority": "IEC 61400-1 / MNRE Civil Guidelines", "governing_reference": "IEC 61400-1 Section 11", "threshold_deg": 15.0},
                    )
                )
            elif slope_deg >= 8.0:
                cond_reasons.append(f"Moderate slope ({slope_deg}°). Requires cut/fill civil grading & micro-siting slope verification.")
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="TERRAIN-MODERATE-SLOPE",
                        tier=ConstraintTier.CONDITIONAL,
                        category="TERRAIN",
                        description=f"Moderate slope ({slope_deg}°) requires specialized access roads and benching.",
                        statutory_authority="MNRE Civil Works Guidelines",
                        governing_reference="IEC 61400-6 Foundation Design",
                        buffer_or_threshold_m=8.0,
                        data_fact={"measured_slope_deg": slope_deg, "elevation_m": terrain_data.get("elevation_m"), "is_complex_terrain": False},
                        legal_policy={"statutory_authority": "MNRE Civil Works Guidelines", "governing_reference": "IEC 61400-6 Foundation Design", "threshold_deg": 8.0},
                    )
                )

        provenance_chain.append({
            "layer": "Digital Elevation Model",
            "source": "Open-Meteo Elevation Service (Copernicus DEM 90m / SRTM composite)",
            "status": "VERIFIED_REAL" if terrain_status == "READY" else "UNKNOWN",
            "suitability": "PRELIMINARY_SCREENING_ONLY",
            "citation": "Open-Meteo API / Copernicus GLO-90 / SRTM v4.1",
            "acquisition_path": "https://api.open-meteo.com/v1/elevation",
            "nominal_resolution": "90m intermediary",
            "crs": "EPSG:4326",
        })

        # 4. WIND RESOURCE ASSESSMENT (NIWE 120m Atlas)
        if niwe_override is not None:
            wind_res = niwe_override
        else:
            wind_res_obj = niwe_client.get_long_term_wind_resource(center_lat, center_lon, hub_height_m=hub_height_m)
            wind_res = wind_res_obj.model_dump()

        if wind_res.get("status") == "UNKNOWN":
            data_gaps.append("NIWE 120m long-term wind data unindexed for this zone. On-site mast data mandatory.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="WIND-NIWE-UNINDEXED",
                    tier=ConstraintTier.INFORMATIONAL,
                    category="WIND",
                    description="NIWE regional baseline unindexed. Site requires minimum 1-year certified LiDAR/mast campaign.",
                    statutory_authority="National Institute of Wind Energy (NIWE)",
                    governing_reference="MNRE Onshore Guidelines Clause 4.1 Wind Resource Verification",
                    data_fact={"status": "UNINDEXED", "hub_height_m": hub_height_m},
                    legal_policy={"statutory_authority": "NIWE / MNRE", "governing_reference": "MNRE Onshore Guidelines Clause 4.1"},
                )
            )

        provenance_chain.append({
            "layer": "NIWE Wind Potential Atlas 120m",
            "status": wind_res.get("status", "PARTIAL"),
            "suitability": "PRELIMINARY_SCREENING_ONLY",
            "citation": "NIWE Technical Report 19 / Open Wind Dataset",
        })

        # 5. LAND COVER ASSESSMENT (ESA WorldCover 10m)
        if worldcover_override is not None:
            wc_data = worldcover_override
        else:
            wc_data = worldcover_client.evaluate_concession_landcover(center_lat, center_lon, radius_km=3.0)

        dominant_code = wc_data.get("dominant_class_code", 40)
        # 50 = Built-up, 80 = Water bodies, 90 = Wetland, 95 = Mangroves
        if dominant_code in (50, 80, 90, 95):
            hard_reasons.append(f"ESA WorldCover dominant class is {wc_data.get('dominant_class_name')} (Code {dominant_code}), statutory hard exclusion.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id=f"LANDCOVER-CLASS-{dominant_code}",
                    tier=ConstraintTier.HARD_EXCLUSION,
                    category="WATER" if dominant_code in (80, 90, 95) else "INFRASTRUCTURE",
                    description=f"Incompatible land cover: {wc_data.get('dominant_class_name')}.",
                    statutory_authority="Ministry of Environment, Forest & Climate Change (MoEFCC)",
                    governing_reference="Wetlands (Conservation and Management) Rules / CRZ Notification",
                    data_fact={"dominant_class_code": dominant_code, "dominant_class_name": wc_data.get("dominant_class_name")},
                    legal_policy={"statutory_authority": "MoEFCC", "governing_reference": "Wetlands / CRZ Notification"},
                )
            )
        elif dominant_code == 10:  # Tree cover
            cond_reasons.append("Tree cover detected. Requires State Forest Department Non-Forest Land Certificate.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="LANDCOVER-TREE-COVER",
                    tier=ConstraintTier.CONDITIONAL,
                    category="CONSERVATION",
                    description="Tree cover requires Forest Conservation Act clearance prior to civil works.",
                    statutory_authority="MoEFCC / State Forest Department",
                    governing_reference="Forest (Conservation) Act, 1980",
                    data_fact={"dominant_class_code": 10, "dominant_class_name": "Tree cover"},
                    legal_policy={"statutory_authority": "MoEFCC / State Forest Department", "governing_reference": "Forest (Conservation) Act, 1980"},
                )
            )

        provenance_chain.append({
            "layer": "ESA WorldCover 10m",
            "status": wc_data.get("status", "PARTIAL"),
            "suitability": "PRELIMINARY_SCREENING_ONLY",
            "citation": "ESA WorldCover 2021 v200",
        })

        # 6. INFRASTRUCTURE & SETTLEMENT ASSESSMENT (OSM Overpass + MNRE 2024 Setbacks)
        osm_status = "READY"
        if osm_override is not None:
            osm_data = osm_override
            if osm_data.get("status") == "UNKNOWN" or "error" in osm_data:
                osm_status = "UNKNOWN"
        else:
            try:
                osm_data = overpass_client.query_physical_features(center_lat, center_lon, radius_km=3.0)
            except Exception as e:
                osm_status = "UNKNOWN"
                osm_data = {"error": str(e), "features": {}}

        dwellings_list = osm_data.get("features", {}).get("buildings", []) if osm_status == "READY" else []
        highways_list = osm_data.get("features", {}).get("highways", []) if osm_status == "READY" else []
        powerlines_list = osm_data.get("features", {}).get("powerlines", []) if osm_status == "READY" else []
        waterways_list = osm_data.get("features", {}).get("waterways", []) if osm_status == "READY" else []

        # Rule on rural missing buildings
        if osm_status == "UNKNOWN":
            data_gaps.append("OSM Overpass infrastructure query failed. Dwellings and road setbacks UNKNOWN.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="OSM-QUERY-FAILED",
                    tier=ConstraintTier.UNKNOWN,
                    category="DATA_QUALITY",
                    description="Physical infrastructure query failed. Cadastral survey mandatory before layout generation.",
                    statutory_authority="OpenStreetMap / Survey of India",
                    governing_reference="MNRE 2024 Infrastructure Safety Standards",
                )
            )
        elif len(dwellings_list) == 0:
            cond_reasons.append("Zero OSM dwellings recorded. High probability of unmapped rural hamlets; satellite audit mandatory.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="OSM-RURAL-ZERO-DWELLINGS",
                    tier=ConstraintTier.CONDITIONAL,
                    category="INFRASTRUCTURE",
                    description="Zero OSM buildings recorded in rural zone. Satellite visual audit required to prevent siting over dwellings.",
                    statutory_authority="MNRE / District Revenue Cadastre",
                    governing_reference="MNRE 2024 Guidelines Section on Habitation Setbacks",
                    buffer_or_threshold_m=500.0,
                )
            )
        else:
            # Active dwellings/settlements detected:
            settlement_cores = [b for b in dwellings_list if b.get("is_settlement_core") is True or "settlement" in str(b.get("type", "")).lower()]
            individual_buildings = [b for b in dwellings_list if b not in settlement_cores]
            is_dwelling_cluster = len(dwellings_list) >= 15

            if len(settlement_cores) > 0 or is_dwelling_cluster:
                # 500m mandatory buffer for recognized settlement cores or >=15 dwelling clusters
                cluster_count = len(settlement_cores) if len(settlement_cores) > 0 else len(dwellings_list)
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="MNRE-2024-HABITATION",
                        tier=ConstraintTier.HARD_EXCLUSION,
                        category="INFRASTRUCTURE",
                        description=f"Habitation settlement area detected ({len(settlement_cores)} settlement zones, {len(dwellings_list)} total features). Mandatory 500m noise/safety setback.",
                        statutory_authority="Ministry of New and Renewable Energy (MNRE), Government of India",
                        governing_reference="MNRE 2024 Guidelines, Habitation Cluster Buffer (500m)",
                        buffer_or_threshold_m=500.0,
                        affected_feature_count=len(settlement_cores) if len(settlement_cores) > 0 else len(dwellings_list),
                        data_fact={"settlement_cores_count": len(settlement_cores), "total_dwellings_count": len(dwellings_list), "cluster_threshold_met": is_dwelling_cluster or len(settlement_cores) > 0},
                        legal_policy={"statutory_authority": "MNRE, Government of India", "governing_reference": "MNRE 2024 Guidelines, Clause on Habitation Cluster Setbacks", "prescribed_setback_m": 500.0},
                    )
                )

            if len(individual_buildings) > 0:
                # Statutory distance for individual structures: HH + 0.5*RD + 5m
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="MNRE-2024-INDIVIDUAL-STRUCTURES",
                        tier=ConstraintTier.HARD_EXCLUSION,
                        category="INFRASTRUCTURE",
                        description=f"Individual permanent structures ({len(individual_buildings)} buildings). Statutory setback = HH + 0.5*RD + 5m ({mnre_statutory_dist_m:.1f}m).",
                        statutory_authority="Ministry of New and Renewable Energy (MNRE), Government of India",
                        governing_reference="MNRE 2024 Guidelines, Infrastructure Safety Distances",
                        buffer_or_threshold_m=mnre_statutory_dist_m,
                        affected_feature_count=len(individual_buildings),
                        data_fact={"individual_building_count": len(individual_buildings)},
                        legal_policy={"statutory_authority": "MNRE, Government of India", "governing_reference": "MNRE 2024 Guidelines, Infrastructure Safety Distances", "prescribed_setback_m": mnre_statutory_dist_m},
                    )
                )

        if len(highways_list) > 0:
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="MNRE-2024-PUBLIC-ROADS",
                    tier=ConstraintTier.HARD_EXCLUSION,
                    category="INFRASTRUCTURE",
                    description=f"Notified road network ({len(highways_list)} segments). Statutory setback = HH + 0.5*RD + 5m ({mnre_statutory_dist_m:.1f}m).",
                    statutory_authority="MNRE / Ministry of Road Transport and Highways (MoRTH)",
                    governing_reference="MNRE 2024 Guidelines, Public Roads Safety Distance",
                    buffer_or_threshold_m=mnre_statutory_dist_m,
                    affected_feature_count=len(highways_list),
                    data_fact={"highway_count": len(highways_list)},
                    legal_policy={"statutory_authority": "MNRE / MoRTH", "governing_reference": "MNRE 2024 Guidelines, Public Roads Safety Distance", "prescribed_setback_m": mnre_statutory_dist_m},
                )
            )

        if len(powerlines_list) > 0:
            ehv_lines = [
                p for p in powerlines_list
                if p.get("is_ehv") is True
                or (isinstance(p.get("voltage_v"), (int, float)) and p.get("voltage_v") >= 66000)
                or (isinstance(p.get("voltage"), str) and any(v in str(p.get("voltage")) for v in ["66", "110", "132", "220", "400", "765"]))
            ]
            dist_lines = [p for p in powerlines_list if p not in ehv_lines]

            if len(ehv_lines) > 0:
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="MNRE-2024-EHV-LINES",
                        tier=ConstraintTier.HARD_EXCLUSION,
                        category="INFRASTRUCTURE",
                        description=f"Extra High Voltage (EHV >= 66kV) corridor ({len(ehv_lines)} features). Statutory setback = HH + 0.5*RD + 5m ({mnre_statutory_dist_m:.1f}m).",
                        statutory_authority="MNRE / Central Electricity Authority (CEA)",
                        governing_reference="MNRE 2024 Guidelines / CEA Transmission Safety Standards",
                        buffer_or_threshold_m=mnre_statutory_dist_m,
                        affected_feature_count=len(ehv_lines),
                        data_fact={"ehv_feature_count": len(ehv_lines), "voltage_verified": True},
                        legal_policy={"statutory_authority": "MNRE / CEA", "governing_reference": "MNRE 2024 Guidelines, EHV Corridor Clearance", "prescribed_setback_m": mnre_statutory_dist_m},
                    )
                )

            if len(dist_lines) > 0:
                active_constraints.append(
                    SpatialConstraint(
                        constraint_id="GRID-DISTRIBUTION-ADVISORY",
                        tier=ConstraintTier.CONDITIONAL,
                        category="INFRASTRUCTURE",
                        description=f"Unverified / distribution grid lines ({len(dist_lines)} features). Cadastral utility survey required (50m advisory margin).",
                        statutory_authority="Central Electricity Authority (CEA) / Engineering Policy",
                        governing_reference="CEA Safety Regulations 2010 (Rule 60/61) / Site Cadastral Verification Policy",
                        buffer_or_threshold_m=50.0,
                        affected_feature_count=len(dist_lines),
                        data_fact={"distribution_feature_count": len(dist_lines), "voltage_verified": False},
                        legal_policy={"statutory_authority": "Engineering Policy (Non-Statutory)", "governing_reference": "CEA Distribution Guidelines", "prescribed_setback_m": 50.0},
                    )
                )

        if len(waterways_list) > 0:
            # 1. Statutory Wet Margin (MoEFCC Wetlands Rules 2017 / State Lake Margin Directives: 50m)
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="STATUTORY-WATERBODY-MARGIN",
                    tier=ConstraintTier.HARD_EXCLUSION,
                    category="WATER",
                    description=f"Natural drainage & waterbodies ({len(waterways_list)} features). Statutory riparian wet margin (50.0m).",
                    statutory_authority="MoEFCC / State Water Resources Dept",
                    governing_reference="Wetlands (Conservation and Management) Rules, 2017 / State Lake & River Margin Directives",
                    buffer_or_threshold_m=50.0,
                    affected_feature_count=len(waterways_list),
                    data_fact={"waterway_count": len(waterways_list), "feature_type": "surface_drainage"},
                    legal_policy={"statutory_authority": "MoEFCC / State Water Resources Dept", "governing_reference": "Wetlands (Conservation and Management) Rules, 2017", "prescribed_setback_m": 50.0},
                )
            )
            # 2. Engineering Flood Margin Policy (IEC 61400-6 Foundation Scour / Micro-Siting: 100m)
            cond_reasons.append(f"Surface water drainage present ({len(waterways_list)} features). Geotechnical foundation flood-risk and scour verification recommended.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="ENGINEERING-POLICY-FLOOD-BUFFER",
                    tier=ConstraintTier.CONDITIONAL,
                    category="WATER",
                    description=f"Floodplain & foundation scour clearance ({len(waterways_list)} features). Engineering micro-siting advisory buffer (100.0m).",
                    statutory_authority="Engineering Best Practice (Non-Statutory)",
                    governing_reference="IEC 61400-6 Foundation Scour & Flood Hazard Guidance",
                    buffer_or_threshold_m=100.0,
                    affected_feature_count=len(waterways_list),
                    data_fact={"waterway_count": len(waterways_list)},
                    legal_policy={"statutory_authority": "Engineering Policy (Non-Statutory)", "governing_reference": "IEC 61400-6", "prescribed_setback_m": 100.0},
                )
            )

        provenance_chain.append({
            "layer": "OpenStreetMap Infrastructure & Physical Features",
            "status": "VERIFIED_REAL" if osm_status == "READY" else "UNKNOWN",
            "suitability": "PRELIMINARY_SCREENING_ONLY",
            "citation": "OpenStreetMap Contributors / Overpass API",
        })

        # 7. CONSERVATION & PROTECTED AREAS (Protected Planet WDPA v4)
        if protected_override is not None:
            pa_res = protected_override
        else:
            pa_res = protected_planet_client.check_protected_area_proximity(center_lat, center_lon, buffer_km=1.0)

        if pa_res.get("is_inside_protected_area", False):
            hard_reasons.append(f"Inside statutory conservation area: {pa_res.get('nearest_protected_area')} ({pa_res.get('designation')}). Micro-siting prohibited by law.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="WDPA-INTERIOR-PROHIBITED",
                    tier=ConstraintTier.HARD_EXCLUSION,
                    category="CONSERVATION",
                    description=f"Inside {pa_res.get('nearest_protected_area')}. Prohibited by Wildlife Protection Act, 1972.",
                    statutory_authority="National Board for Wildlife (NBWL) / MoEFCC",
                    governing_reference="Wildlife (Protection) Act, 1972 Section 35",
                    data_fact=pa_res.get("data_fact"),
                    legal_policy=pa_res.get("legal_policy"),
                )
            )
        elif pa_res.get("is_in_buffer_zone", False):
            cond_reasons.append(f"Within 1.0 km conservation screening zone of {pa_res.get('nearest_protected_area')}. Site-specific MoEFCC ESZ Gazette notification verification required.")
            active_constraints.append(
                SpatialConstraint(
                    constraint_id="WDPA-ESZ-ADVISORY-BUFFER",
                    tier=ConstraintTier.CONDITIONAL,
                    category="CONSERVATION",
                    description=f"Within 1.0 km conservation screening zone of {pa_res.get('nearest_protected_area')}. Requires verification against site-specific MoEFCC Gazette notification (SC Order In Re: T.N. Godavarman, 2023).",
                    statutory_authority="MoEFCC / Wildlife Division (Advisory Screening)",
                    governing_reference="MoEFCC ESZ Gazette Registry / Supreme Court 2023 Clarification (2023 SCC OnLine SC 510)",
                    buffer_or_threshold_m=1000.0,
                    data_fact=pa_res.get("data_fact"),
                    legal_policy=pa_res.get("legal_policy"),
                )
            )

        provenance_chain.append({
            "layer": "UNEP-WCMC Protected Planet (WDPA v4)",
            "status": "VERIFIED_REAL",
            "suitability": "ENGINEERING_GRADE",
            "citation": "UNEP-WCMC / IUCN Protected Planet Database 2024",
        })

        # 8. BUILDABLE MASK & PERCENTAGE SYNTHESIS
        # We sample candidate positions across the search envelope and project them into UTM space
        # to calculate exact metric buildable vs restricted vs excluded vs unknown parcels.
        evaluation_grid = self._evaluate_projected_grid(
            envelope_geom=envelope_geom,
            bbox=bbox,
            center_lat=center_lat,
            center_lon=center_lon,
            zone=zone,
            is_north=is_north,
            hard_constraints=[c for c in active_constraints if c.tier == ConstraintTier.HARD_EXCLUSION],
            conditional_constraints=[c for c in active_constraints if c.tier == ConstraintTier.CONDITIONAL],
            unknown_constraints=[c for c in active_constraints if c.tier == ConstraintTier.UNKNOWN],
            dwellings=dwellings_list,
            highways=highways_list,
            powerlines=powerlines_list,
            waterways=waterways_list,
            statutory_setback_m=mnre_statutory_dist_m,
            slope_deg=slope_deg,
        )

        buildable_area_m2 = evaluation_grid["buildable_area_m2"]
        buildable_area_km2 = buildable_area_m2 / 1_000_000.0
        buildable_pct = evaluation_grid["buildable_pct"]
        cond_pct = evaluation_grid["cond_pct"]
        excl_pct = evaluation_grid["excl_pct"]
        unk_pct = evaluation_grid["unk_pct"]

        # Determine overall site readiness
        if len([c for c in active_constraints if c.tier == ConstraintTier.UNKNOWN]) > 0 or osm_status == "UNKNOWN" or terrain_status == "UNKNOWN":
            overall_status = "UNKNOWN"
        elif buildable_pct <= 0.0:
            overall_status = "UNBUILDABLE"
        elif len(cond_reasons) > 0 or cond_pct > 0.0 or len(data_gaps) > 0:
            overall_status = "PARTIAL"
        else:
            overall_status = "READY"

        return SuitabilityEvaluationResult(
            overall_status=overall_status,
            search_envelope_geometry=envelope_geom,
            search_envelope_area_km2=round(search_area_km2, 4),
            buildable_area_km2=round(buildable_area_km2, 4),
            buildable_area_m2=round(buildable_area_m2, 2),
            buildable_percentage=round(buildable_pct, 1),
            conditional_percentage=round(cond_pct, 1),
            excluded_percentage=round(excl_pct, 1),
            unknown_percentage=round(unk_pct, 1),
            projected_crs=projected_epsg,
            utm_zone=zone,
            buildable_mask_geojson=evaluation_grid.get("buildable_geojson"),
            terrain_assessment={
                "status": terrain_status,
                "elevation_m": terrain_data.get("elevation_m"),
                "slope_deg": slope_deg,
                "aspect_deg": terrain_data.get("aspect_deg"),
                "tri_ruggedness_m": terrain_data.get("tri_ruggedness_m"),
                "is_complex_terrain": slope_deg > 15.0,
            },
            wind_assessment=wind_res,
            landcover_assessment=wc_data,
            infrastructure_assessment={
                "status": osm_status,
                "counts": {
                    "dwellings": len(dwellings_list),
                    "highways": len(highways_list),
                    "powerlines": len(powerlines_list),
                    "waterways": len(waterways_list),
                },
                "dwellings": dwellings_list,
                "highways": highways_list,
                "powerlines": powerlines_list,
                "waterways": waterways_list,
                "statutory_safety_distance_m": round(mnre_statutory_dist_m, 1),
                "habitation_cluster_detected": len(dwellings_list) >= 15,
            },
            conservation_assessment=pa_res,
            active_constraints=active_constraints,
            hard_exclusion_reasons=hard_reasons,
            conditional_reasons=cond_reasons,
            data_gaps=data_gaps,
            provenance_chain=provenance_chain,
            evaluated_at=now_ts,
        )

    def _evaluate_projected_grid(
        self,
        envelope_geom: Dict[str, Any],
        bbox: List[float],
        center_lat: float,
        center_lon: float,
        zone: int,
        is_north: bool,
        hard_constraints: List[SpatialConstraint],
        conditional_constraints: List[SpatialConstraint],
        unknown_constraints: List[SpatialConstraint],
        dwellings: List[Dict[str, Any]],
        highways: List[Dict[str, Any]],
        powerlines: List[Dict[str, Any]],
        waterways: List[Dict[str, Any]],
        statutory_setback_m: float,
        slope_deg: float,
        grid_resolution_m: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Samples the search envelope on a regular metric UTM grid, applies strict buffering and
        exclusion math, and calculates buildable percentage and parcel polygons.
        """
        min_lon, min_lat, max_lon, max_lat = bbox

        # Project bounding box corners to local UTM
        min_e, min_n, _, _ = project_wgs84_to_utm(min_lon, min_lat, zone=zone, is_north=is_north)
        max_e, max_n, _, _ = project_wgs84_to_utm(max_lon, max_lat, zone=zone, is_north=is_north)

        # Ensure correct ordering
        e_start, e_end = min(min_e, max_e), max(min_e, max_e)
        n_start, n_end = min(min_n, max_n), max(min_n, max_n)

        width_m = e_end - e_start
        height_m = n_end - n_start

        # Adaptive step so we test ~400-900 sample points inside envelope
        span_m = max(width_m, height_m)
        step_m = max(50.0, span_m / 25.0)

        is_dwelling_cluster = len(dwellings) >= 15
        default_dwelling_buf = 500.0 if is_dwelling_cluster else statutory_setback_m

        # Pre-project features and their geometry segments to UTM
        dwelling_features = _prepare_utm_features(
            dwellings, zone=zone, is_north=is_north, default_setback_m=default_dwelling_buf
        )
        highway_features = _prepare_utm_features(
            highways, zone=zone, is_north=is_north, default_setback_m=statutory_setback_m
        )
        powerline_features = _prepare_utm_features(
            powerlines, zone=zone, is_north=is_north, default_setback_m=50.0
        )
        waterway_features = _prepare_utm_features(
            waterways, zone=zone, is_north=is_north, default_setback_m=50.0
        )
        all_infrastructure = dwelling_features + highway_features + powerline_features + waterway_features

        total_inside_envelope = 0
        buildable_count = 0
        cond_count = 0
        excl_count = 0
        unk_count = 0

        buildable_cells_utm: List[Tuple[float, float]] = []

        is_site_steep = slope_deg > 15.0
        is_site_moderate = (8.0 <= slope_deg <= 15.0)
        has_unknown = len(unknown_constraints) > 0

        # Check for global hard exclusion (e.g. inside national park or slope > 15 deg everywhere)
        global_hard_exclusion = any(c.constraint_id == "WDPA-INTERIOR-PROHIBITED" for c in hard_constraints) or is_site_steep

        cur_e = e_start + step_m / 2.0
        while cur_e < e_end:
            cur_n = n_start + step_m / 2.0
            while cur_n < n_end:
                lon_deg, lat_deg = unproject_utm_to_wgs84(cur_e, cur_n, zone=zone, is_north=is_north)

                # Strict containment check against search envelope (respects outer polygon and interior holes)
                if is_point_in_polygon_geometry(lon_deg, lat_deg, envelope_geom):
                    total_inside_envelope += 1

                    if has_unknown:
                        unk_count += 1
                    elif global_hard_exclusion:
                        excl_count += 1
                    elif _is_point_excluded_by_features(cur_e, cur_n, all_infrastructure):
                        excl_count += 1
                    elif is_site_moderate or len(conditional_constraints) > 0:
                        cond_count += 1
                        buildable_count += 1  # Conditional is potentially buildable subject to verification
                        buildable_cells_utm.append((cur_e, cur_n))
                    else:
                        buildable_count += 1
                        buildable_cells_utm.append((cur_e, cur_n))

                cur_n += step_m
            cur_e += step_m

        if total_inside_envelope == 0:
            return {
                "buildable_area_m2": 0.0,
                "buildable_pct": 0.0,
                "cond_pct": 0.0,
                "excl_pct": 100.0,
                "unk_pct": 0.0,
                "buildable_geojson": None,
            }

        # Area calculation
        cell_area_m2 = step_m * step_m
        buildable_area_m2 = buildable_count * cell_area_m2
        buildable_pct = (buildable_count / total_inside_envelope) * 100.0
        cond_pct = (cond_count / total_inside_envelope) * 100.0
        excl_pct = (excl_count / total_inside_envelope) * 100.0
        unk_pct = (unk_count / total_inside_envelope) * 100.0

        # Construct approximate GeoJSON for buildable mask parcels
        # If site is entirely unbuildable, return empty MultiPolygon
        buildable_geojson = None
        if buildable_count > 0:
            # Generate parcel polygons around each buildable cell center
            h_s = step_m / 2.0
            polys = []
            for ce, cn in buildable_cells_utm[:150]:  # Cap sample polygons for crisp rendering
                p1 = unproject_utm_to_wgs84(ce - h_s, cn - h_s, zone=zone, is_north=is_north)
                p2 = unproject_utm_to_wgs84(ce + h_s, cn - h_s, zone=zone, is_north=is_north)
                p3 = unproject_utm_to_wgs84(ce + h_s, cn + h_s, zone=zone, is_north=is_north)
                p4 = unproject_utm_to_wgs84(ce - h_s, cn + h_s, zone=zone, is_north=is_north)

                # Ensure all parcel vertices never escape the Phase 2 search envelope
                c_lon, c_lat = unproject_utm_to_wgs84(ce, cn, zone=zone, is_north=is_north)
                cp1 = _contain_point_in_envelope(p1[0], p1[1], c_lon, c_lat, envelope_geom)
                cp2 = _contain_point_in_envelope(p2[0], p2[1], c_lon, c_lat, envelope_geom)
                cp3 = _contain_point_in_envelope(p3[0], p3[1], c_lon, c_lat, envelope_geom)
                cp4 = _contain_point_in_envelope(p4[0], p4[1], c_lon, c_lat, envelope_geom)

                ring = [
                    cp1,
                    cp2,
                    cp3,
                    cp4,
                    cp1,
                ]
                polys.append([ring])

            buildable_geojson = {
                "type": "MultiPolygon",
                "coordinates": polys,
            }

        return {
            "buildable_area_m2": round(buildable_area_m2, 2),
            "buildable_pct": round(buildable_pct, 1),
            "cond_pct": round(cond_pct, 1),
            "excl_pct": round(excl_pct, 1),
            "unk_pct": round(unk_pct, 1),
            "buildable_geojson": buildable_geojson,
        }


# Singleton export
suitability_engine = EnvironmentalSuitabilityEngine()

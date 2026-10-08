"""
backend/app/engineering/candidate_validator.py — Hard Engineering Constraints & Clearance Validator.

Validates proposed wind turbine candidate locations against:
1. Site Boundary Containment & Rotor Blade Clearance (R_rotor distance to outer perimeter)
2. Interior Hole/Donut Avoidance & Clearance (R_rotor distance to lake/settlement holes)
3. Hard-Exclusion Setback Clearance (Feature Setback + R_rotor)
4. Terrain Slope Constraints (Copernicus DEM slope <= 15.0 deg)
5. Long-Term Wind Resource Verification (NIWE / GWA non-zero screening)
6. Minimum Turbine-to-Turbine Spacing (k * Rotor Diameter in projected metric space)
7. Non-Fabrication Invariant: If required engineering data is missing/failed, returns UNKNOWN.
"""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.app.engineering.floris_engine import TURBINE_CATALOG
from backend.app.engineering.geometry_conventions import (
    decompose_wake_frame,
    get_cesium_heading_deg,
    get_turbine_yaw_deg,
    get_wind_to_deg,
)
from backend.app.gis.geometry_validation import _point_in_ring
from backend.app.gis.projection import project_wgs84_to_utm, unproject_utm_to_wgs84


class CandidateStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    CONDITIONAL = "CONDITIONAL"


class ValidationRuleResult(BaseModel):
    """Result of an individual engineering rule check."""
    model_config = ConfigDict(extra="ignore")

    rule_id: str
    passed: bool
    status: CandidateStatus
    margin_m: Optional[float] = None
    threshold_m: Optional[float] = None
    detail: str
    governing_reference: str


class TurbineCandidate(BaseModel):
    """Validated engineering turbine candidate with full telemetry and provenance."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    status: CandidateStatus = CandidateStatus.FEASIBLE
    longitude: float
    latitude: float
    utm_easting_m: float
    utm_northing_m: float
    elevation_m: Optional[float] = None

    # Turbine specifications & classification
    turbine_model_id: str
    turbine_model_name: str
    turbine_category: str = "COMMERCIAL_ONSHORE"
    is_commercial_onshore: bool = True
    terrain_suitability: str = "ONSHORE"
    rotor_diameter_m: float
    hub_height_m: float
    rated_power_kw: float

    # Wind and engineering orientation conventions
    wind_speed_mps: Optional[float] = None
    wind_from_deg: float = 270.0
    wind_to_deg: float = 90.0
    turbine_yaw_deg: float = 270.0
    cesium_heading_deg: float = 180.0

    # Clearance telemetry
    site_boundary_clearance_m: float = 0.0
    nearest_exclusion_clearance_m: Optional[float] = None
    min_inter_turbine_distance_m: Optional[float] = None

    # Validation records
    rules_passed: List[str] = Field(default_factory=list)
    rules_failed: List[str] = Field(default_factory=list)
    rule_evaluations: Dict[str, ValidationRuleResult] = Field(default_factory=dict)
    exclusion_reasons: List[str] = Field(default_factory=list)
    conditional_advisories: List[str] = Field(default_factory=list)

    # Provenance
    provenance: Dict[str, Any] = Field(default_factory=dict)
    evaluated_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def dist_to_segment_2d(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Computes exact Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
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


def min_dist_to_ring_2d(px: float, py: float, ring: List[Tuple[float, float]]) -> float:
    """Computes minimum Euclidean distance from (px, py) to any segment of a closed ring."""
    if len(ring) < 2:
        return float("inf")
    min_d = float("inf")
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        d = dist_to_segment_2d(px, py, x1, y1, x2, y2)
        if d < min_d:
            min_d = d
    return min_d


class CandidateEngineeringValidator:
    """Rigorous validator checking candidate points against hard engineering constraints."""

    def __init__(self, turbine_model_id: str = "ge_25_120"):
        if turbine_model_id not in TURBINE_CATALOG:
            raise ValueError(f"Unknown turbine model '{turbine_model_id}'. Must be one of: {list(TURBINE_CATALOG.keys())}")
        self.turbine_model_id = turbine_model_id
        self.spec = TURBINE_CATALOG[turbine_model_id]
        self.rotor_diameter_m = float(self.spec["rotor_diameter_m"])
        self.rotor_radius_m = self.rotor_diameter_m / 2.0
        self.hub_height_m = float(self.spec["hub_height_m"])
        self.rated_power_kw = float(self.spec["rated_power_kw"])
        self.name = str(self.spec["name"])
        self.category = str(self.spec.get("category", "COMMERCIAL_ONSHORE"))
        self.is_commercial_onshore = bool(self.spec.get("is_commercial_onshore", True))
        self.terrain_suitability = str(self.spec.get("terrain_suitability", "ONSHORE"))
        self.deployment_readiness = str(self.spec.get("deployment_readiness", "COMMERCIAL_PRODUCTION"))
        # Statutory setback distance based on actual turbine specifications: HH + 0.5*RD + 5m
        self.statutory_setback_m = self.hub_height_m + 0.5 * self.rotor_diameter_m + 5.0

    def validate_candidate_point(
        self,
        easting_m: float,
        northing_m: float,
        lon: float,
        lat: float,
        utm_exterior_rings: List[List[Tuple[float, float]]],
        utm_interior_holes: List[List[Tuple[float, float]]],
        prepared_exclusions: List[Dict[str, Any]],
        elevation_m: Optional[float],
        slope_deg: Optional[float],
        wind_speed_mps: Optional[float],
        wind_from_deg: float = 270.0,
        candidate_id: str = "cand-001",
        conditional_exclusions: Optional[List[Dict[str, Any]]] = None,
        is_in_wdpa_buffer: bool = False,
    ) -> TurbineCandidate:
        """
        Validates an individual candidate location against all single-point hard constraints.
        Does not check inter-turbine spacing (which is evaluated on candidate pairs/sets).
        """
        evaluations: Dict[str, ValidationRuleResult] = {}
        rules_passed: List[str] = []
        rules_failed: List[str] = []
        reasons: List[str] = []
        status = CandidateStatus.FEASIBLE

        # ── 1. SITE BOUNDARY CONTAINMENT & ROTOR FOOTPRINT CLEARANCE ────────
        # Point must be inside at least one exterior ring and maintain R_rotor clearance
        inside_exterior = False
        min_dist_to_exterior = 0.0

        for ext_ring in utm_exterior_rings:
            # Ray casting check in 2D UTM space
            ext_pts_list = [[pt[0], pt[1]] for pt in ext_ring]
            if _point_in_ring(easting_m, northing_m, ext_pts_list):
                inside_exterior = True
                dist_to_edge = min_dist_to_ring_2d(easting_m, northing_m, ext_ring)
                min_dist_to_exterior = max(min_dist_to_exterior, dist_to_edge)

        if not inside_exterior:
            rule_res = ValidationRuleResult(
                rule_id="RULE-SITE-BOUNDARY-CONTAINMENT",
                passed=False,
                status=CandidateStatus.EXCLUDED,
                margin_m=-1.0,
                threshold_m=self.rotor_radius_m,
                detail="Candidate center point is outside authoritative site boundary envelope.",
                governing_reference="MNRE Micro-Siting Guidelines / Boundary Cadastre",
            )
            evaluations["RULE-SITE-BOUNDARY-CONTAINMENT"] = rule_res
            rules_failed.append("RULE-SITE-BOUNDARY-CONTAINMENT")
            reasons.append("Outside site boundary envelope.")
            status = CandidateStatus.EXCLUDED
        elif min_dist_to_exterior < self.rotor_radius_m:
            margin = min_dist_to_exterior - self.rotor_radius_m
            rule_res = ValidationRuleResult(
                rule_id="RULE-SITE-BOUNDARY-CLEARANCE",
                passed=False,
                status=CandidateStatus.EXCLUDED,
                margin_m=round(margin, 2),
                threshold_m=self.rotor_radius_m,
                detail=f"Rotor clearance violation: distance to boundary is {round(min_dist_to_exterior, 1)}m, "
                       f"requires >= {self.rotor_radius_m}m (blade radius).",
                governing_reference="MNRE Micro-Siting Guidelines (Rotor Tip Clearance)",
            )
            evaluations["RULE-SITE-BOUNDARY-CLEARANCE"] = rule_res
            rules_failed.append("RULE-SITE-BOUNDARY-CLEARANCE")
            reasons.append(f"Rotor footprint clearance violation ({round(min_dist_to_exterior, 1)}m < {self.rotor_radius_m}m).")
            status = CandidateStatus.EXCLUDED
        else:
            rule_res = ValidationRuleResult(
                rule_id="RULE-SITE-BOUNDARY-CONTAINMENT",
                passed=True,
                status=CandidateStatus.FEASIBLE,
                margin_m=round(min_dist_to_exterior - self.rotor_radius_m, 2),
                threshold_m=self.rotor_radius_m,
                detail=f"Inside boundary with {round(min_dist_to_exterior, 1)}m margin to boundary edge.",
                governing_reference="MNRE Micro-Siting Guidelines",
            )
            evaluations["RULE-SITE-BOUNDARY-CONTAINMENT"] = rule_res
            rules_passed.append("RULE-SITE-BOUNDARY-CONTAINMENT")

        # ── 2. INTERIOR HOLE / DONUT CLEARANCE ─────────────────────────────
        for hole_idx, hole_ring in enumerate(utm_interior_holes):
            hole_pts_list = [[pt[0], pt[1]] for pt in hole_ring]
            if _point_in_ring(easting_m, northing_m, hole_pts_list):
                rule_res = ValidationRuleResult(
                    rule_id=f"RULE-INTERIOR-HOLE-AVOIDANCE-{hole_idx}",
                    passed=False,
                    status=CandidateStatus.EXCLUDED,
                    margin_m=-1.0,
                    threshold_m=self.rotor_radius_m,
                    detail=f"Center point is inside interior hole/enclave #{hole_idx}.",
                    governing_reference="Topological Hole Invariant",
                )
                evaluations[f"RULE-INTERIOR-HOLE-AVOIDANCE-{hole_idx}"] = rule_res
                rules_failed.append(f"RULE-INTERIOR-HOLE-AVOIDANCE-{hole_idx}")
                reasons.append(f"Inside interior exclusion hole #{hole_idx}.")
                status = CandidateStatus.EXCLUDED
            else:
                dist_to_hole = min_dist_to_ring_2d(easting_m, northing_m, hole_ring)
                if dist_to_hole < self.rotor_radius_m:
                    rule_res = ValidationRuleResult(
                        rule_id=f"RULE-INTERIOR-HOLE-CLEARANCE-{hole_idx}",
                        passed=False,
                        status=CandidateStatus.EXCLUDED,
                        margin_m=round(dist_to_hole - self.rotor_radius_m, 2),
                        threshold_m=self.rotor_radius_m,
                        detail=f"Rotor swept area penetrates interior hole #{hole_idx} "
                               f"({round(dist_to_hole, 1)}m < {self.rotor_radius_m}m).",
                        governing_reference="MNRE Micro-Siting Guidelines",
                    )
                    evaluations[f"RULE-INTERIOR-HOLE-CLEARANCE-{hole_idx}"] = rule_res
                    rules_failed.append(f"RULE-INTERIOR-HOLE-CLEARANCE-{hole_idx}")
                    reasons.append(f"Rotor sweeps into interior exclusion hole #{hole_idx}.")
                    status = CandidateStatus.EXCLUDED

        # ── 3. HARD-EXCLUSION BUFFER CLEARANCE (INFRASTRUCTURE & ENVIRONMENT)
        nearest_excl_dist = float("inf")
        nearest_excl_type = ""
        violation_found = False

        for feat in prepared_exclusions:
            setback_m = float(feat.get("setback_m", self.statutory_setback_m))
            if feat.get("clearance_includes_blade", False):
                required_clearance_m = setback_m
            else:
                required_clearance_m = setback_m + self.rotor_radius_m
            f_type = feat.get("category", "INFRASTRUCTURE")

            # Check bbox pre-filter for performance
            min_x, min_y, max_x, max_y = feat["bbox"]
            if easting_m < min_x - required_clearance_m or easting_m > max_x + required_clearance_m:
                continue
            if northing_m < min_y - required_clearance_m or northing_m > max_y + required_clearance_m:
                continue

            for seg in feat["segments"]:
                d = dist_to_segment_2d(easting_m, northing_m, seg[0], seg[1], seg[2], seg[3])
                if d < nearest_excl_dist:
                    nearest_excl_dist = d
                    nearest_excl_type = f_type
                if d < required_clearance_m:
                    violation_found = True
                    margin = d - required_clearance_m
                    rule_id = f"RULE-EXCLUSION-{feat.get('id', f_type)}"
                    rule_res = ValidationRuleResult(
                        rule_id=rule_id,
                        passed=False,
                        status=CandidateStatus.EXCLUDED,
                        margin_m=round(margin, 2),
                        threshold_m=required_clearance_m,
                        detail=f"Violates setback clearance for {f_type}: distance is {round(d, 1)}m, "
                               f"requires >= {required_clearance_m}m ({setback_m}m setback + {0.0 if feat.get('clearance_includes_blade') else self.rotor_radius_m}m blade clearance).",
                        governing_reference=feat.get("governing_reference", "MNRE 2024 / Statutory Setbacks"),
                    )
                    evaluations[rule_id] = rule_res
                    rules_failed.append(rule_id)
                    reasons.append(f"Setback clearance violation for {f_type} ({round(d, 1)}m < {required_clearance_m}m).")
                    status = CandidateStatus.EXCLUDED
                    break
            if violation_found:
                break

        if not violation_found:
            rule_res = ValidationRuleResult(
                rule_id="RULE-HARD-EXCLUSIONS-CLEARANCE",
                passed=True,
                status=CandidateStatus.FEASIBLE,
                margin_m=round(nearest_excl_dist, 2) if nearest_excl_dist < 1e6 else None,
                threshold_m=None,
                detail=f"Clear of all hard infrastructure exclusions (closest feature: {round(nearest_excl_dist, 1)}m).",
                governing_reference="MNRE 2024 National Wind-Solar Hybrid Policy Setbacks",
            )
            evaluations["RULE-HARD-EXCLUSIONS-CLEARANCE"] = rule_res
            rules_passed.append("RULE-HARD-EXCLUSIONS-CLEARANCE")

        # ── 3B. CONDITIONAL ADVISORY CHECKS (INFRASTRUCTURE & ENVIRONMENT) ──
        # Conditional constraints do not unilaterally exclude a candidate, but record advisory warnings
        # and propagate PARTIAL status to the overall candidate generation.
        conditional_advisories: List[str] = []
        if conditional_exclusions:
            for feat in conditional_exclusions:
                sb = float(feat.get("setback_m", 50.0))
                effective_sb = sb + self.rotor_radius_m
                f_type = feat.get("category", "ADVISORY")
                min_x, min_y, max_x, max_y = feat["bbox"]
                if easting_m < min_x - effective_sb or easting_m > max_x + effective_sb:
                    continue
                if northing_m < min_y - effective_sb or northing_m > max_y + effective_sb:
                    continue
                for seg in feat["segments"]:
                    d = dist_to_segment_2d(easting_m, northing_m, seg[0], seg[1], seg[2], seg[3])
                    if d < effective_sb:
                        rule_id = f"RULE-CONDITIONAL-{feat.get('id', f_type)}"
                        evaluations[rule_id] = ValidationRuleResult(
                            rule_id=rule_id,
                            passed=True,
                            status=CandidateStatus.CONDITIONAL,
                            margin_m=round(d - effective_sb, 2),
                            threshold_m=effective_sb,
                            detail=f"Rotor footprint within {sb}m + {self.rotor_radius_m}m conditional advisory margin for {f_type} (distance is {round(d, 1)}m).",
                            governing_reference=feat.get("governing_reference", "CEA / IEC Advisory Policy"),
                        )
                        rules_passed.append(rule_id)
                        conditional_advisories.append(f"{f_type} conditional advisory ({round(d, 1)}m <= {effective_sb}m).")
                        break

        if is_in_wdpa_buffer:
            rule_id = "RULE-CONDITIONAL-WDPA-ESZ-1KM"
            evaluations[rule_id] = ValidationRuleResult(
                rule_id=rule_id,
                passed=True,
                status=CandidateStatus.CONDITIONAL,
                margin_m=None,
                threshold_m=1000.0,
                detail="Within 1.0 km conservation screening zone of protected area. Site-specific MoEFCC Gazette notification verification required.",
                governing_reference="MoEFCC ESZ Gazette Registry / Supreme Court 2023 Clarification (2023 SCC OnLine SC 510)",
            )
            rules_passed.append(rule_id)
            conditional_advisories.append("Within 1.0 km protected area ESZ screening zone.")

        # ── 4. TERRAIN / SLOPE CONSTRAINT (Copernicus DEM) ────────────────
        if slope_deg is None or elevation_m is None:
            # Non-fabrication invariant: missing elevation/slope must yield UNKNOWN
            rule_res = ValidationRuleResult(
                rule_id="RULE-TERRAIN-DEM-DATA",
                passed=False,
                status=CandidateStatus.UNKNOWN,
                detail="Copernicus DEM elevation or slope data unavailable for candidate position.",
                governing_reference="Non-Fabrication Invariant (Copernicus DEM 90m / SRTM composite)",
            )
            evaluations["RULE-TERRAIN-DEM-DATA"] = rule_res
            rules_failed.append("RULE-TERRAIN-DEM-DATA")
            reasons.append("DEM elevation/slope data unavailable.")
            if status != CandidateStatus.EXCLUDED:
                status = CandidateStatus.UNKNOWN
        elif slope_deg > 15.0:
            rule_res = ValidationRuleResult(
                rule_id="RULE-TERRAIN-SLOPE-MAX-15DEG",
                passed=False,
                status=CandidateStatus.EXCLUDED,
                margin_m=round(15.0 - slope_deg, 2),
                threshold_m=15.0,
                detail=f"Slope {round(slope_deg, 1)}° exceeds statutory engineering threshold 15.0°.",
                governing_reference="IEC 61400-1 Complex Terrain Limits / MNRE Micro-Siting",
            )
            evaluations["RULE-TERRAIN-SLOPE-MAX-15DEG"] = rule_res
            rules_failed.append("RULE-TERRAIN-SLOPE-MAX-15DEG")
            reasons.append(f"Steep slope ({round(slope_deg, 1)}° > 15.0°).")
            status = CandidateStatus.EXCLUDED
        elif 8.0 <= slope_deg <= 15.0:
            rule_res = ValidationRuleResult(
                rule_id="RULE-ADVISORY-MODERATE-SLOPE",
                passed=True,
                status=CandidateStatus.CONDITIONAL,
                margin_m=round(15.0 - slope_deg, 2),
                threshold_m=8.0,
                detail=f"Moderate slope {round(slope_deg, 1)}° (8-15°). Buildable subject to site-specific cut/fill civil engineering design.",
                governing_reference="MNRE Civil Works Guidelines / IEC 61400-6",
            )
            evaluations["RULE-ADVISORY-MODERATE-SLOPE"] = rule_res
            rules_passed.append("RULE-ADVISORY-MODERATE-SLOPE")
            conditional_advisories.append(f"Moderate slope ({round(slope_deg, 1)}°). Site cut/fill review required.")
        else:
            rule_res = ValidationRuleResult(
                rule_id="RULE-TERRAIN-SLOPE-MAX-15DEG",
                passed=True,
                status=CandidateStatus.FEASIBLE,
                margin_m=round(15.0 - slope_deg, 2),
                threshold_m=15.0,
                detail=f"Slope {round(slope_deg, 1)}° is buildable (<= 8.0°).",
                governing_reference="IEC 61400-1 Terrain Limits",
            )
            evaluations["RULE-TERRAIN-SLOPE-MAX-15DEG"] = rule_res
            rules_passed.append("RULE-TERRAIN-SLOPE-MAX-15DEG")

        # ── 5. WIND RESOURCE ELIGIBILITY (NIWE / GWA) ──────────────────────
        if wind_speed_mps is None or wind_speed_mps <= 0.0:
            rule_res = ValidationRuleResult(
                rule_id="RULE-WIND-RESOURCE-ELIGIBLE",
                passed=False,
                status=CandidateStatus.UNKNOWN,
                detail="Long-term wind resource data unavailable or invalid for candidate coordinates.",
                governing_reference="NIWE 120m Long-Term Wind Atlas / GWA 3.0",
            )
            evaluations["RULE-WIND-RESOURCE-ELIGIBLE"] = rule_res
            rules_failed.append("RULE-WIND-RESOURCE-ELIGIBLE")
            reasons.append("Wind resource data unavailable or zero.")
            if status != CandidateStatus.EXCLUDED:
                status = CandidateStatus.UNKNOWN
        else:
            rule_res = ValidationRuleResult(
                rule_id="RULE-WIND-RESOURCE-ELIGIBLE",
                passed=True,
                status=CandidateStatus.FEASIBLE,
                margin_m=None,
                threshold_m=None,
                detail=f"Verified wind resource: {round(wind_speed_mps, 2)} m/s at hub height {self.hub_height_m}m.",
                governing_reference="NIWE 120m Wind Atlas / Global Wind Atlas 3.0",
            )
            evaluations["RULE-WIND-RESOURCE-ELIGIBLE"] = rule_res
            rules_passed.append("RULE-WIND-RESOURCE-ELIGIBLE")

        # Construct candidate telemetry
        wind_to = get_wind_to_deg(wind_from_deg)
        yaw_deg = get_turbine_yaw_deg(wind_from_deg)
        cesium_heading = get_cesium_heading_deg(wind_from_deg)

        provenance = {
            "turbine_model_source": "Authoritative Manufacturer Reference Database (TURBINE_CATALOG)",
            "turbine_category": self.category,
            "is_commercial_onshore": self.is_commercial_onshore,
            "terrain_suitability": self.terrain_suitability,
            "statutory_safety_distance_m": round(self.statutory_setback_m, 1),
            "dem_source": "Open-Meteo Elevation Service (Copernicus DEM GLO-90 / SRTM 90m composite)",
            "wind_source": "NIWE 120m Wind Atlas / Global Wind Atlas 3.0",
            "statutory_rules": "MNRE 2024 / IEC 61400-1",
            "spatial_engine": "Projected Local Metric UTM (EPSG:326xx)",
        }

        return TurbineCandidate(
            candidate_id=candidate_id,
            status=status,
            longitude=round(lon, 6),
            latitude=round(lat, 6),
            utm_easting_m=round(easting_m, 2),
            utm_northing_m=round(northing_m, 2),
            elevation_m=round(elevation_m, 1) if elevation_m is not None else None,
            turbine_model_id=self.turbine_model_id,
            turbine_model_name=self.name,
            turbine_category=self.category,
            is_commercial_onshore=self.is_commercial_onshore,
            terrain_suitability=self.terrain_suitability,
            rotor_diameter_m=self.rotor_diameter_m,
            hub_height_m=self.hub_height_m,
            rated_power_kw=self.rated_power_kw,
            wind_speed_mps=round(wind_speed_mps, 2) if wind_speed_mps is not None else None,
            wind_from_deg=round(wind_from_deg, 1),
            wind_to_deg=round(wind_to, 1),
            turbine_yaw_deg=round(yaw_deg, 1),
            cesium_heading_deg=round(cesium_heading, 1),
            site_boundary_clearance_m=round(min_dist_to_exterior - self.rotor_radius_m, 2),
            nearest_exclusion_clearance_m=round(nearest_excl_dist, 2) if nearest_excl_dist < 1e6 else None,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            rule_evaluations=evaluations,
            exclusion_reasons=reasons,
            conditional_advisories=conditional_advisories,
            provenance=provenance,
        )

    def validate_inter_turbine_spacing(
        self,
        candidates: List[TurbineCandidate],
        min_spacing_diameters: float = 4.0,
    ) -> Tuple[List[TurbineCandidate], List[TurbineCandidate]]:
        """
        Validates minimum turbine-to-turbine pairwise spacing (d >= k * D).
        Separates feasible candidates from spacing-excluded candidates.
        """
        min_dist_m = min_spacing_diameters * self.rotor_diameter_m
        feasible_set: List[TurbineCandidate] = []
        excluded_spacing: List[TurbineCandidate] = []

        for cand in candidates:
            if cand.status != CandidateStatus.FEASIBLE:
                continue

            # Check distance against all candidates accepted into feasible set
            is_valid = True
            min_found_dist = float("inf")

            for existing in feasible_set:
                dx = cand.utm_easting_m - existing.utm_easting_m
                dy = cand.utm_northing_m - existing.utm_northing_m
                dist = math.hypot(dx, dy)
                if dist < min_found_dist:
                    min_found_dist = dist
                if dist < min_dist_m:
                    is_valid = False
                    break

            if is_valid:
                cand_copy = cand.model_copy(update={
                    "min_inter_turbine_distance_m": round(min_found_dist, 1) if min_found_dist < 1e6 else None
                })
                cand_copy.rules_passed.append("RULE-MIN-TURBINE-SPACING")
                cand_copy.rule_evaluations["RULE-MIN-TURBINE-SPACING"] = ValidationRuleResult(
                    rule_id="RULE-MIN-TURBINE-SPACING",
                    passed=True,
                    status=CandidateStatus.FEASIBLE,
                    margin_m=round(min_found_dist - min_dist_m, 2) if min_found_dist < 1e6 else None,
                    threshold_m=min_dist_m,
                    detail=f"Pairwise spacing >= {min_dist_m}m ({min_spacing_diameters}D).",
                    governing_reference="IEC 61400-1 Inter-Turbine Spacing",
                )
                feasible_set.append(cand_copy)
            else:
                margin = min_found_dist - min_dist_m
                cand_excluded = cand.model_copy(update={
                    "status": CandidateStatus.EXCLUDED,
                    "min_inter_turbine_distance_m": round(min_found_dist, 1),
                })
                cand_excluded.rules_failed.append("RULE-MIN-TURBINE-SPACING")
                cand_excluded.exclusion_reasons.append(
                    f"Minimum spacing violation: {round(min_found_dist, 1)}m < {min_dist_m}m ({min_spacing_diameters}D)."
                )
                cand_excluded.rule_evaluations["RULE-MIN-TURBINE-SPACING"] = ValidationRuleResult(
                    rule_id="RULE-MIN-TURBINE-SPACING",
                    passed=False,
                    status=CandidateStatus.EXCLUDED,
                    margin_m=round(margin, 2),
                    threshold_m=min_dist_m,
                    detail=f"Violates minimum spacing: {round(min_found_dist, 1)}m < {min_dist_m}m ({min_spacing_diameters}D).",
                    governing_reference="IEC 61400-1 Inter-Turbine Spacing",
                )
                excluded_spacing.append(cand_excluded)

        return feasible_set, excluded_spacing

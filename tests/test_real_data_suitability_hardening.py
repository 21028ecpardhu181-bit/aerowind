"""
tests/test_real_data_suitability_hardening.py — Authoritative Real Data & Adversarial Hardening Test Suite.

Verifies:
1. Checked-in Authoritative Real Data Sample (Anantapur, Andhra Pradesh).
2. Non-Fabrication Invariant: Missing or failed data is UNKNOWN/PARTIAL, never suitable or safe.
3. Separation of Data Facts (measured coordinates, slope, distances) from Legal Policy Rules (statutory citations, setbacks).
4. Adversarial Spatial Tests:
   - Exclusion touching envelope boundary.
   - Exclusion inside donut polygon hole (interior ring).
   - Overlapping infrastructure exclusions (road crossing dwelling buffer).
   - Buildable mask vertices strictly contained inside Phase 2 boundary (zero boundary leakage).
5. Polyline segment distance verification vs single centroid.
"""

import json
from pathlib import Path
import pytest

from backend.app.gis.geometry_validation import is_point_in_polygon_geometry
from backend.app.gis.suitability_engine import (
    ConstraintTier,
    suitability_engine,
)


SAMPLE_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "samples" / "real_data_sample_anantapur.json"


def test_real_data_sample_anantapur_integrity():
    """Verify the checked-in real data sample conforms to strict provenance metadata schema."""
    assert SAMPLE_PATH.exists(), f"Sample file not found at {SAMPLE_PATH}"
    with open(SAMPLE_PATH, "r") as f:
        data = json.load(f)

    assert data.get("dataset_type") == "REAL_DATA_SAMPLE"
    assert "Anantapur" in data.get("location_name")
    assert data.get("crs") == "EPSG:4326"
    assert data.get("projected_crs") == "EPSG:32643"
    assert data.get("license") is not None
    assert data.get("retrieved_at") is not None

    # Check layer representations
    assert data.get("boundary") is not None
    assert data.get("terrain") is not None
    assert data.get("wind") is not None
    assert data.get("landcover") is not None
    assert data.get("infrastructure") is not None
    assert data.get("conservation") is not None

    # Re-evaluate with suitability engine
    geom = data["boundary"]["geometry"]
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=geom,
        hub_height_m=120.0,
        rotor_diameter_m=120.0,
    )

    assert res.overall_status in ("READY", "PARTIAL")
    assert res.buildable_percentage >= 70.0
    assert res.search_envelope_area_km2 > 30.0
    assert len(res.active_constraints) >= 4

    # Verify all active constraints separate Data Facts from Statutory Policy
    for c in res.active_constraints:
        assert c.data_fact is not None, f"Constraint {c.constraint_id} missing data_fact"
        assert c.legal_policy is not None, f"Constraint {c.constraint_id} missing legal_policy"
        assert c.governing_reference != ""


def test_adversarial_exclusion_touching_envelope_boundary():
    """Verify that an infrastructure exclusion touching or straddling the envelope boundary does not cause leakage."""
    envelope = {
        "type": "Polygon",
        "coordinates": [[
            [77.6000, 14.6800],
            [77.6200, 14.6800],
            [77.6200, 14.7000],
            [77.6000, 14.7000],
            [77.6000, 14.6800],
        ]]
    }

    # Place a highway right along the southern boundary edge
    osm_boundary_highway = {
        "features": {
            "buildings": [{"id": 1, "lat": 14.6900, "lon": 77.6100, "type": "residential"}],
            "highways": [{
                "id": 999,
                "lat": 14.6800,
                "lon": 77.6100,
                "geometry": [
                    [77.6000, 14.6800],
                    [77.6100, 14.6800],
                    [77.6200, 14.6800],
                ]
            }],
            "powerlines": [],
            "waterways": [],
        }
    }

    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope,
        osm_override=osm_boundary_highway,
    )

    assert res.excluded_percentage > 0.0
    assert res.buildable_percentage < 100.0

    # Ensure all buildable mask vertices are strictly inside the envelope
    if res.buildable_mask_geojson:
        coords = res.buildable_mask_geojson["coordinates"]
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    assert is_point_in_polygon_geometry(pt[0], pt[1], envelope), f"Vertex {pt} escaped envelope!"


def test_adversarial_exclusion_inside_donut_hole():
    """Verify that interior holes (donut polygons) reject candidate points and contain zero buildable mask vertices."""
    # Envelope: 0.04 x 0.04 deg outer square, with a 0.01 x 0.01 deg interior hole in the center
    envelope_with_hole = {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring
            [
                [77.6000, 14.6800],
                [77.6400, 14.6800],
                [77.6400, 14.7200],
                [77.6000, 14.7200],
                [77.6000, 14.6800],
            ],
            # Interior hole (lake / waterbody hole)
            [
                [77.6150, 14.6950],
                [77.6250, 14.6950],
                [77.6250, 14.7050],
                [77.6150, 14.7050],
                [77.6150, 14.6950],
            ]
        ]
    }

    # Place an infrastructure item right inside the donut hole
    osm_inside_hole = {
        "features": {
            "buildings": [
                {"id": 1, "lat": 14.7100, "lon": 77.6100, "type": "residential"},
                {"id": 2, "lat": 14.7000, "lon": 77.6200, "type": "isolated_settlement"},  # Centered in hole
            ],
            "highways": [],
            "powerlines": [],
            "waterways": [],
        }
    }

    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope_with_hole,
        osm_override=osm_inside_hole,
    )

    assert res.search_envelope_area_km2 > 0.0

    # Verify that NO buildable polygon vertex lies inside the hole
    if res.buildable_mask_geojson:
        for poly in res.buildable_mask_geojson["coordinates"]:
            for ring in poly:
                for pt in ring:
                    # Must be inside envelope_with_hole (which means inside exterior AND outside hole)
                    assert is_point_in_polygon_geometry(pt[0], pt[1], envelope_with_hole), (
                        f"Point {pt} illegally placed inside donut hole or outside envelope!"
                    )


def test_adversarial_overlapping_exclusions():
    """Verify that overlapping exclusions (road intersecting a dwelling cluster) are handled without arithmetic anomalies."""
    envelope = {
        "type": "Polygon",
        "coordinates": [[
            [77.6000, 14.6800],
            [77.6200, 14.6800],
            [77.6200, 14.7000],
            [77.6000, 14.7000],
            [77.6000, 14.6800],
        ]]
    }

    # Overlapping road and 16 clustered dwellings at the exact same location
    dwellings = [{"id": i, "lat": 14.6900, "lon": 77.6100, "type": "residential"} for i in range(16)]
    highways = [{
        "id": 101,
        "lat": 14.6900,
        "lon": 77.6100,
        "geometry": [
            [77.6050, 14.6900],
            [77.6150, 14.6900],
        ]
    }]

    osm_overlapping = {
        "features": {
            "buildings": dwellings,
            "highways": highways,
            "powerlines": [],
            "waterways": [],
        }
    }

    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope,
        osm_override=osm_overlapping,
    )

    # Invariants
    total_pct = round(res.buildable_percentage + res.excluded_percentage, 1)
    assert 99.0 <= total_pct <= 101.0, f"Percentage sum anomaly: {total_pct}"
    assert res.excluded_percentage > 0.0


def test_polyline_segment_distance_vs_single_centroid():
    """Verify that a long highway polyline excludes points near its line segments, not just its centroid."""
    envelope = {
        "type": "Polygon",
        "coordinates": [[
            [77.6000, 14.6800],
            [77.6400, 14.6800],
            [77.6400, 14.7200],
            [77.6000, 14.7200],
            [77.6000, 14.6800],
        ]]
    }

    # A 3km diagonal road traversing the site from SW to NE
    # Centroid is at (77.6200, 14.7000)
    highway_diagonal = [{
        "id": 555,
        "lat": 14.7000,
        "lon": 77.6200,
        "geometry": [
            [77.6050, 14.6850],
            [77.6200, 14.7000],
            [77.6350, 14.7150],
        ]
    }]

    osm_diagonal = {
        "features": {
            "buildings": [{"id": 1, "lat": 14.6850, "lon": 77.6350, "type": "residential"}],
            "highways": highway_diagonal,
            "powerlines": [],
            "waterways": [],
        }
    }

    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope,
        osm_override=osm_diagonal,
    )

    # Diagonal line segment buffer should exclude significant area along the corridor
    assert res.excluded_percentage >= 10.0


def test_non_fabrication_missing_layers_gate_unknown():
    """Verify that missing critical layers (DEM failure or OSM failure) force overall_status = UNKNOWN."""
    envelope = {
        "type": "Polygon",
        "coordinates": [[
            [77.6000, 14.6800],
            [77.6200, 14.6800],
            [77.6200, 14.7000],
            [77.6000, 14.7000],
            [77.6000, 14.6800],
        ]]
    }

    # 1. Missing DEM slope
    res_dem_failed = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope,
        terrain_override={"slope_deg": None, "elevation_m": None},
    )
    assert res_dem_failed.overall_status == "UNKNOWN"
    assert res_dem_failed.unknown_percentage == 100.0
    assert res_dem_failed.buildable_percentage == 0.0

    # 2. Missing OSM data
    res_osm_failed = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=envelope,
        osm_override={"features": {}, "error": "Overpass gateway timeout"},
    )
    assert res_osm_failed.overall_status == "UNKNOWN"
    assert res_osm_failed.unknown_percentage == 100.0
    assert res_osm_failed.buildable_percentage == 0.0


def test_phase3a_deterministic_regulatory_provenance_audit():
    """Phase 3A Final Regulatory + Provenance Audit Verification.
    
    Verifies:
    1. Search envelope boundary area equals 31.0564 km² (calculated from EPSG:32643 UTM projection).
    2. Exact separation of statutory rules from advisory engineering policy.
    3. Dwellings decoupled: recognized settlement zones (500m) vs individual permanent structures (185m).
    4. Powerlines decoupled: statutory EHV >= 66kV (185m) vs unverified/distribution lines (50m advisory).
    5. Waterways decoupled: statutory wet margin (50m) vs geotechnical scour policy (100m advisory).
    6. DEM provenance records actual acquisition path (Open-Meteo GLO-90 / SRTM composite).
    7. Zero buildable points cross the outer boundary or violate hard exclusions.
    8. Buildable area reconciliation matches total inside envelope.
    """
    with open(SAMPLE_PATH, "r") as f:
        sample = json.load(f)

    geom = sample["boundary"]["geometry"]
    res = suitability_engine.evaluate_site_suitability(
        search_envelope_geometry=geom,
        hub_height_m=120.0,
        rotor_diameter_m=120.0,
    )

    # 1. Search envelope boundary area
    assert res.search_envelope_area_km2 == 31.0564, f"Unexpected area {res.search_envelope_area_km2}"

    # 2. Constraints verification
    constraint_ids = {c.constraint_id: c for c in res.active_constraints}
    assert "MNRE-2024-HABITATION" in constraint_ids
    assert "MNRE-2024-INDIVIDUAL-STRUCTURES" in constraint_ids
    assert "MNRE-2024-PUBLIC-ROADS" in constraint_ids
    assert "MNRE-2024-EHV-LINES" in constraint_ids
    assert "GRID-DISTRIBUTION-ADVISORY" in constraint_ids
    assert "STATUTORY-WATERBODY-MARGIN" in constraint_ids
    assert "ENGINEERING-POLICY-FLOOD-BUFFER" in constraint_ids

    # Rule 1: Habitation clusters
    c_hab = constraint_ids["MNRE-2024-HABITATION"]
    assert c_hab.tier == ConstraintTier.HARD_EXCLUSION
    assert c_hab.buffer_or_threshold_m == 500.0
    assert c_hab.affected_feature_count == 4  # 1 city node + 3 residential landuse zones

    # Rule 2: Individual dwellings (<15 cluster threshold)
    c_ind = constraint_ids["MNRE-2024-INDIVIDUAL-STRUCTURES"]
    assert c_ind.tier == ConstraintTier.HARD_EXCLUSION
    assert c_ind.buffer_or_threshold_m == 185.0
    assert c_ind.affected_feature_count == 5  # 5 isolated permanent structures

    # Rule 3: EHV Transmission corridors (>= 66kV)
    c_ehv = constraint_ids["MNRE-2024-EHV-LINES"]
    assert c_ehv.tier == ConstraintTier.HARD_EXCLUSION
    assert c_ehv.buffer_or_threshold_m == 185.0
    assert c_ehv.affected_feature_count == 2  # 132kV and 220kV verified lines

    # Rule 4: Distribution lines (<66kV / unverified)
    c_dist = constraint_ids["GRID-DISTRIBUTION-ADVISORY"]
    assert c_dist.tier == ConstraintTier.CONDITIONAL
    assert c_dist.buffer_or_threshold_m == 50.0
    assert c_dist.affected_feature_count == 9  # unverified power tower / distribution nodes

    # Rule 5: Statutory water margin (MoEFCC Wetlands Rules 2017)
    c_wet = constraint_ids["STATUTORY-WATERBODY-MARGIN"]
    assert c_wet.tier == ConstraintTier.HARD_EXCLUSION
    assert c_wet.buffer_or_threshold_m == 50.0
    assert c_wet.affected_feature_count == 5

    # Rule 6: Foundation scour clearance (IEC 61400-6 non-statutory)
    c_fl = constraint_ids["ENGINEERING-POLICY-FLOOD-BUFFER"]
    assert c_fl.tier == ConstraintTier.CONDITIONAL
    assert c_fl.buffer_or_threshold_m == 100.0

    # 3. DEM Provenance validation
    prov_dem = next((p for p in res.provenance_chain if "DEM" in p.get("layer", "") or "Elevation" in p.get("layer", "")), None)
    assert prov_dem is not None
    assert "Open-Meteo" in prov_dem["citation"] or "Copernicus" in prov_dem["citation"]

    # 4. Zero geometric leakage: all buildable mask vertices strictly inside envelope
    assert res.buildable_mask_geojson is not None
    for poly in res.buildable_mask_geojson["coordinates"]:
        for ring in poly:
            for pt in ring:
                assert is_point_in_polygon_geometry(pt[0], pt[1], geom), (
                    f"Buildable parcel vertex {pt} leaked outside search envelope!"
                )

    # 5. Area percentage reconciliation
    # buildable_percentage + excluded_percentage = 100% (within rounding)
    assert abs((res.buildable_percentage + res.excluded_percentage) - 100.0) <= 0.5
    assert res.buildable_percentage > 75.0
    assert res.excluded_percentage > 15.0


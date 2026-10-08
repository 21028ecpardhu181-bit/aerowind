"""
tests/test_qubo_readiness_audit.py
Phase 5.1: Final Physical-Model & QUBO-Readiness Audit Test Suite.

Validates:
1. Wind resource provenance & runtime retrieval path (SOURCE_DEFINED vs DERIVED).
2. Offline reproducibility of Anantapur climatology from serialized inputs.
3. Height extrapolation audit across all supported turbine hub heights (90m to 150m).
4. Loss accounting classification audit (ENGINEERING_ASSUMPTION vs DERIVED).
5. Exact FLORIS configuration serialization.
6. Formal QUBO approximation error audit (Exact FLORIS vs Pairwise QUBO across subsets).
7. Three-turbine inline nonlinear wake check (deficit saturation proof).
8. Full 16-sector directional resource contract.
9. End-to-end AEP physical sanity bounds and zero-fabrication failure guards.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from scipy.stats import spearmanr

from backend.app.engineering.aep_engine import aep_calculation_engine
from backend.app.engineering.floris_engine import FlorisWakeEngine, TURBINE_CATALOG, interpolate_turbine_power_and_ct
from backend.app.engineering.geometry_conventions import decompose_wake_frame
from backend.app.engineering.wind_resource_service import wind_resource_service, WindResourceRecord
from backend.app.provenance import EngineeringSuitability, SourceStatus


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "backend" / "data" / "samples" / "real_data_sample_anantapur.json"


# ── TEST 1: WIND RESOURCE PROVENANCE & RUNTIME RETRIEVAL PATH ─────────────────

def test_niwe_resource_provenance_and_runtime_path():
    """Prove exact NIWE resource retrieval path, dataset version, and classifications."""
    res = wind_resource_service.get_long_term_resource(14.6815, 77.6005, hub_height_m=110.0, ground_elevation_m=347.0)

    assert res.status == "READY"
    assert "National Institute of Wind Energy (NIWE)" in res.data_source
    assert "Technical Report 19" in res.dataset_version
    assert "500m" in res.spatial_resolution
    assert res.hub_height_m == 110.0

    # Provenance classifications
    assert res.weibull_source == "SOURCE_DEFINED"
    assert res.directional_sector_source == "DERIVED"
    assert res.air_density_source == "DERIVED"
    assert res.shear_scaling_source == "DERIVED"

    # Serialized inputs present
    assert res.serialized_resource_inputs is not None
    assert res.serialized_resource_inputs["station_reference"] == "NIWE-AP-AN-01"
    assert res.serialized_resource_inputs["source_elevation_agl_m"] == 120.0
    assert res.serialized_resource_inputs["source_mean_speed_mps"] == 7.42
    assert res.serialized_resource_inputs["source_weibull_a_mps"] == 8.37
    assert res.serialized_resource_inputs["source_weibull_k"] == 2.28
    assert res.serialized_resource_inputs["source_predominant_direction_deg"] == 265.0


# ── TEST 2: RESOURCE REPRODUCIBILITY FROM SERIALIZED INPUTS ───────────────────

def test_resource_reproducibility_from_serialized_inputs():
    """Prove that reported A, k, mean speed, wind rose, and density are 100% reproducible offline."""
    serialized = wind_resource_service.get_serialized_resource_inputs(14.6815, 77.6005, hub_height_m=110.0, ground_elevation_m=347.0)

    assert serialized["reproducibility_verified"] is True
    # Reference values
    u_ref = serialized["source_mean_speed_mps"]  # 7.42
    a_ref = serialized["source_weibull_a_mps"]   # 8.37
    k_ref = serialized["source_weibull_k"]       # 2.28
    h_ref = serialized["source_elevation_agl_m"] # 120.0
    h_tgt = serialized["target_hub_height_m"]    # 110.0
    alpha = serialized["shear_exponent_alpha"]   # 0.14
    z_asl = serialized["ground_elevation_asl_m"] # 347.0

    # Reproduce height extrapolation: u(h) = u_ref * (h / h_ref)^alpha
    reproduced_u = round(u_ref * ((h_tgt / h_ref) ** alpha), 2)
    assert reproduced_u == serialized["scaled_mean_wind_speed_mps"]
    assert reproduced_u == 7.33

    reproduced_a = round(a_ref * ((h_tgt / h_ref) ** alpha), 2)
    assert reproduced_a == serialized["scaled_weibull_a_mps"]
    assert reproduced_a == 8.27

    # Reproduce barometric air density: rho(z) = 1.225 * exp(-z / 8434.5)
    reproduced_rho = round(1.225 * np.exp(-z_asl / 8434.5), 3)
    assert reproduced_rho == serialized["air_density_kgm3"]
    assert reproduced_rho == 1.176

    # Verify 16 sectors sum to 100%
    sectors = serialized["wind_rose_16"]
    assert len(sectors) == 16
    sum_freq = round(sum(s["frequency_pct"] for s in sectors), 2)
    assert sum_freq == 100.0


# ── TEST 3: HEIGHT EXTRAPOLATION AUDIT ACROSS ALL TURBINES ────────────────────

def test_height_extrapolation_audit_all_supported_turbines():
    """Verify system never assumes 120m == 110m, and test all supported turbine heights."""
    ref_speed = 7.42
    alpha = 0.14

    # 1. NREL 5-MW (H = 90m)
    u_90 = wind_resource_service.scale_wind_shear_power_law(ref_speed, 90.0, 120.0, alpha=alpha)
    assert u_90 == 7.13
    assert u_90 < ref_speed

    # 2. Vestas V110-2.0 (H = 95m)
    u_95 = wind_resource_service.scale_wind_shear_power_law(ref_speed, 95.0, 120.0, alpha=alpha)
    assert u_95 == 7.18
    assert u_95 < ref_speed

    # 3. GE 2.5-120 (H = 110m)
    u_110 = wind_resource_service.scale_wind_shear_power_law(ref_speed, 110.0, 120.0, alpha=alpha)
    assert u_110 == 7.33
    assert u_110 < ref_speed

    # 4. SG 3.4-132 (H = 114m)
    u_114 = wind_resource_service.scale_wind_shear_power_law(ref_speed, 114.0, 120.0, alpha=alpha)
    assert u_114 == 7.37
    assert u_114 < ref_speed

    # 5. IEA 15-MW (H = 150m)
    u_150 = wind_resource_service.scale_wind_shear_power_law(ref_speed, 150.0, 120.0, alpha=alpha)
    assert u_150 == 7.66
    assert u_150 > ref_speed

    # Hierarchy invariant
    assert u_90 < u_95 < u_110 < u_114 < ref_speed < u_150


# ── TEST 4: LOSS ACCOUNTING CLASSIFICATION AUDIT ──────────────────────────────

def test_loss_accounting_classification_audit():
    """Audit the classification of loss items: ENGINEERING_ASSUMPTION vs DERIVED."""
    positions = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 45.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 45.0},
    ]
    res = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="ge_25_120")

    losses = res.losses
    assert losses.loss_breakdown is not None
    breakdown_map = {item["name"]: item for item in losses.loss_breakdown}

    # Technical losses are project assumptions, not IEC-prescribed values
    assert breakdown_map["electrical_loss"]["classification"] == "ENGINEERING_ASSUMPTION"
    assert breakdown_map["availability_loss"]["classification"] == "ENGINEERING_ASSUMPTION"
    assert breakdown_map["curtailment_loss"]["classification"] == "ENGINEERING_ASSUMPTION"
    assert breakdown_map["environmental_loss"]["classification"] == "ENGINEERING_ASSUMPTION"
    assert breakdown_map["hysteresis_loss"]["classification"] == "ENGINEERING_ASSUMPTION"

    # Wake loss and total BoP derate are derived
    assert breakdown_map["wake_loss"]["classification"] == "DERIVED"
    assert breakdown_map["total_bop_loss"]["classification"] == "DERIVED"

    # IEC standard framework reference
    assert "IEC 61400-15-1:2025" in res.assumptions_doc["loss_accounting_framework"]
    assert "ENGINEERING_ASSUMPTION" in res.assumptions_doc["loss_classification_note"]


# ── TEST 5: FLORIS CONFIGURATION SERIALIZATION ────────────────────────────────

def test_floris_configuration_serialization():
    """Verify serialized FLORIS configuration contains exact parameters used in runtime."""
    engine = FlorisWakeEngine("ge_25_120")
    config = engine.get_floris_configuration()

    assert config["wake_velocity_model"] == "gauss"
    assert config["wake_expansion_parameter_k_star"] == 0.04
    assert config["superposition_method"] == "Katic et al. (1986) sum-of-squares velocity deficit combination"
    assert config["maximum_deficit_ceiling"] == 0.65
    assert config["rotor_diameter_m"] == 120.0
    assert config["hub_height_m"] == 110.0
    assert config["rated_power_kw"] == 2500.0
    assert config["directional_sectors_count"] == 16


# ── TEST 6: FORMAL QUBO APPROXIMATION ERROR AUDIT ─────────────────────────────

def test_exact_vs_pairwise_wake_qubo_approximation_audit():
    """
    Formally evaluate exact multi-turbine FLORIS vs pairwise QUBO across all candidate subsets.
    Verifies error metrics, RMS error, Spearman ranking correlation, and documents differences.
    """
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    from backend.app.engineering.candidate_engine import candidate_engine
    p4_gen = candidate_engine.generate_candidates(
        search_envelope_geometry=data["boundary"]["geometry"],
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=6,
    )

    cands = [
        {
            "id": c.candidate_id,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "utm_easting_m": c.utm_easting_m,
            "utm_northing_m": c.utm_northing_m,
            "elevation_m": c.elevation_m or 347.0,
        }
        for c in p4_gen.feasible_candidates[:6]
    ]

    audit = aep_calculation_engine.audit_qubo_approximation_accuracy(
        candidate_positions=cands,
        turbine_model_id="ge_25_120",
        site_elevation_m=347.0,
        max_audit_candidates=6,
    )

    assert audit["status"] == "AUDIT_COMPLETED"
    assert audit["candidate_count_audited"] == 6
    # For 6 candidates, combinations for k=2,3,4: 15 + 20 + 15 = 50 subsets
    assert audit["subsets_evaluated_count"] == 50

    # Measured approximation bounds:
    # Error should be modest (< 2% mean, < 5% max)
    assert audit["mean_percentage_error_pct"] < 2.0
    assert audit["max_percentage_error_pct"] < 5.0
    assert audit["rms_error_mwh"] > 0.0  # Proves non-zero difference between QUBO and FLORIS

    # High ranking correlation (QUBO preserves layout quality ordering)
    assert audit["spearman_rank_correlation"] >= 0.90
    assert "EXACT PHYSICAL EVALUATION" in audit["exact_vs_qubo_semantics"]


# ── TEST 7: THREE-TURBINE INLINE NONLINEAR WAKE CHECK ─────────────────────────

def test_three_turbine_nonlinear_wake_saturation_check():
    """
    Demonstrate that multi-turbine FLORIS deficit combination is nonlinear:
    full FLORIS deficit != sum of independent pairwise deficits.
    """
    engine = FlorisWakeEngine("ge_25_120")
    # 3 turbines in-line facing wind from 270 deg (West -> East):
    # T1 at 0m, T2 at 600m (5D downwind), T3 at 1200m (10D downwind)
    pos_3 = [(0.0, 0.0), (600.0, 0.0), (1200.0, 0.0)]
    res_3 = engine.simulate_farm_wake(pos_3, wind_speed_mps=8.5, wind_direction_deg=270.0)

    # Pairwise individual deficits
    res_13 = engine.simulate_farm_wake([(0.0, 0.0), (1200.0, 0.0)], wind_speed_mps=8.5, wind_direction_deg=270.0)
    res_23 = engine.simulate_farm_wake([(600.0, 0.0), (1200.0, 0.0)], wind_speed_mps=8.5, wind_direction_deg=270.0)

    def_13 = res_13["wake_deficits_pct"][1]  # Deficit on T3 from T1 alone
    def_23 = res_23["wake_deficits_pct"][1]  # Deficit on T3 from T2 alone
    linear_sum_def = def_13 + def_23
    exact_floris_def = res_3["wake_deficits_pct"][2]

    # Exact FLORIS deficit combines via sum-of-squares: sqrt(def_13^2 + def_23^2)
    # Linear addition overestimates deficit because wakes saturate
    assert exact_floris_def < linear_sum_def, "Physical wake deficit saturates; linear sum must strictly overestimate"
    discrepancy = linear_sum_def - exact_floris_def
    assert discrepancy > 5.0, f"Discrepancy must be substantial (>5% deficit points), got {discrepancy}%"


# ── TEST 8: DIRECTIONAL RESOURCE CONTRACT (16 SECTORS) ────────────────────────

def test_directional_resource_contract_16_sectors():
    """Verify Phase 6 contract includes complete 16-sector distribution summing to 100%."""
    candidates = [
        {"id": "C1", "latitude": 14.680, "longitude": 77.600},
        {"id": "C2", "latitude": 14.685, "longitude": 77.605},
    ]
    contract = aep_calculation_engine.build_phase6_performance_contract(candidates, turbine_model_id="ge_25_120")

    clim = contract["wind_climatology"]
    assert "wind_rose_16" in clim
    sectors = clim["wind_rose_16"]
    assert len(sectors) == 16
    assert clim["total_frequency_pct"] == 100.0

    # Sector angles must increment by 22.5 deg
    for i, s in enumerate(sectors):
        assert s["sector_index"] == i
        assert s["wind_from_deg"] == round(i * 22.5, 1)
        assert s["frequency_pct"] >= 0.0
        assert s["mean_speed_mps"] > 0.0
        assert s["weibull_a_mps"] > 0.0


# ── TEST 9: AEP PHYSICAL SANITY BOUNDS ────────────────────────────────────────

def test_aep_physical_sanity_bounds_and_reproducibility():
    """Verify physical sanity bounds hold on reproduced Anantapur 8-turbine layout."""
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    from backend.app.engineering.candidate_engine import candidate_engine
    p4_gen = candidate_engine.generate_candidates(
        search_envelope_geometry=data["boundary"]["geometry"],
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=8,
    )
    cands = [
        {"id": c.candidate_id, "latitude": c.latitude, "longitude": c.longitude, "elevation_m": c.elevation_m or 347.0}
        for c in p4_gen.feasible_candidates[:8]
    ]

    res = aep_calculation_engine.evaluate_layout_aep(cands, turbine_model_id="ge_25_120", site_elevation_m=347.0)

    # Invariants
    theoretical_ceiling = (len(cands) * 2.5 * 8760.0) / 1000.0  # GWh
    assert res.gross_aep_gwh <= theoretical_ceiling
    assert 0.0 <= res.net_capacity_factor_pct <= 100.0
    assert 0.0 <= res.gross_capacity_factor_pct <= 100.0
    assert res.net_aep_gwh <= res.wake_adjusted_aep_gwh <= res.gross_aep_gwh
    assert res.wake_loss_pct >= 0.0

    for turb in res.turbines:
        assert turb.effective_speed_mps <= turb.freestream_speed_mps
        assert turb.gross_energy_mwh >= turb.wake_adjusted_energy_mwh >= turb.net_energy_mwh >= 0.0


# ── TEST 10: FAILURE BEHAVIOR & NON-FABRICATION GUARDS ────────────────────────

def test_failure_behaviour_guards_no_fabrication():
    """Verify missing inputs return UNKNOWN or fail gracefully without fabricating numbers."""
    # 1. Missing / invalid coordinates outside NIWE coverage
    unknown_rec = wind_resource_service.get_long_term_resource(0.0, 0.0, hub_height_m=110.0)
    assert unknown_rec.status == "UNKNOWN"
    assert unknown_rec.annual_mean_wind_speed_mps is None

    # 2. AEP evaluation on unknown wind returns status UNKNOWN
    res_unknown = aep_calculation_engine.evaluate_layout_aep(
        [{"id": "T1", "latitude": 0.0, "longitude": 0.0}],
        wind_resource=unknown_rec,
    )
    assert res_unknown.status == "UNKNOWN"
    assert res_unknown.gross_aep_gwh == 0.0
    assert res_unknown.net_aep_gwh == 0.0

    # 3. Power curve outside catalogue falls back to default safely or rejects
    p_zero, ct_zero = interpolate_turbine_power_and_ct("non_existent_turbine", 0.0)
    assert p_zero == 0.0

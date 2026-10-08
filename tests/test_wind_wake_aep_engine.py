"""
tests/test_wind_wake_aep_engine.py — Comprehensive Test Suite for Phase 5 Wind Resource, Wake & AEP Engine.

Validates all 19 Phase 5 engineering requirements:
1. Wind FROM/TO convention & reversal prevention
2. Height extrapolation & wind shear scaling (source 120m vs target hub heights)
3. Power-curve interpolation, physical bounds [0, P_rated], and cut-in/rated/cut-out
4. Single-turbine freestream baseline (0% wake loss)
5. Downstream wake deficit & physical wake validation (2 turbines)
6. Crosswind separation effect (lateral decay)
7. Downwind separation effect (wake expansion and center recovery)
8. Direction changes & reversal (swapping upstream/downstream roles)
9. Air density handling & IEC 61400-12-1 normalization
10. Explicit IEC 61400-15 loss accounting (electrical, availability, curtailment, environmental, hysteresis)
11. Missing-resource UNKNOWN/UNAVAILABLE propagation (strict non-fabrication)
12. Determinism of repeated identical calculations
13. Model differentiation: different turbine catalogues produce different physical results
14. Real Anantapur sample end-to-end integration test
15. Engineering physical sanity guards (power >= 0, AEP <= rated * 8760, no speed gains)
16. Machine-readable Phase 6 performance contract for QUBO/QAOA
17. FastAPI engineering endpoints integration
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.engineering.aep_engine import (
    AepCalculationEngine,
    AepEvaluationResult,
    aep_calculation_engine,
)
from backend.app.engineering.floris_engine import (
    FlorisWakeEngine,
    TURBINE_CATALOG,
    interpolate_turbine_power_and_ct,
)
from backend.app.engineering.geometry_conventions import (
    decompose_wake_frame,
    get_wind_to_deg,
    get_turbine_yaw_deg,
)
from backend.app.engineering.wind_resource_service import (
    WindResourceRecord,
    wind_resource_service,
)

client = TestClient(app)
SAMPLE_PATH = Path(__file__).resolve().parents[1] / "backend" / "data" / "samples" / "real_data_sample_anantapur.json"


# ── TEST 1: WIND FROM / TO CONVENTION ───────────────────────────────────────

def test_wind_from_to_convention_and_reversal_prevention():
    """Verify wind arrival (FROM) vs downwind travel (TO) convention."""
    # West wind (270 deg) blows TO the East (90 deg)
    assert get_wind_to_deg(270.0) == 90.0
    # North wind (0 deg) blows TO the South (180 deg)
    assert get_wind_to_deg(0.0) == 180.0
    # East wind (90 deg) blows TO the West (270 deg)
    assert get_wind_to_deg(90.0) == 270.0
    # South wind (180 deg) blows TO the North (0 deg)
    assert get_wind_to_deg(180.0) == 0.0

    # Yaw faces upwind into oncoming wind
    assert get_turbine_yaw_deg(270.0) == 270.0

    # Wake coordinate projection:
    # Turbine A at (0, 0), Turbine B at (600, 0) (East of A).
    # If wind is FROM West (270 deg), wind travels TO East (90 deg).
    # Therefore, B is downstream of A (positive downwind distance).
    downwind_m, crosswind_m = decompose_wake_frame(dx_m=600.0, dy_m=0.0, wind_from_deg=270.0)
    assert round(downwind_m, 1) == 600.0
    assert round(crosswind_m, 1) == 0.0

    # If wind is FROM East (90 deg), wind travels TO West (270 deg).
    # Therefore, B is UPSTREAM of A (negative downwind distance).
    downwind_rev, crosswind_rev = decompose_wake_frame(dx_m=600.0, dy_m=0.0, wind_from_deg=90.0)
    assert round(downwind_rev, 1) == -600.0
    assert round(crosswind_rev, 1) == 0.0


# ── TEST 2: HEIGHT EXTRAPOLATION & WIND SHEAR SCALING ────────────────────────

def test_height_extrapolation_and_shear_scaling():
    """Prove that 120m source wind speed does NOT silently equal 110m or 90m hub height."""
    ref_speed_120m = 7.42  # NIWE Anantapur 120m reference
    alpha = 0.14  # Standard IEC neutral shear

    # GE 2.5-120: Hub height = 110m
    speed_110m = wind_resource_service.scale_wind_shear_power_law(ref_speed_120m, 110.0, 120.0, alpha=alpha)
    assert speed_110m < ref_speed_120m, "Wind at 110m must be lower than at 120m"
    expected_110m = round(ref_speed_120m * ((110.0 / 120.0) ** alpha), 2)
    assert speed_110m == expected_110m

    # NREL 5-MW: Hub height = 90m
    speed_90m = wind_resource_service.scale_wind_shear_power_law(ref_speed_120m, 90.0, 120.0, alpha=alpha)
    assert speed_90m < speed_110m, "Wind at 90m must be lower than at 110m"

    # IEA 15-MW: Hub height = 150m
    speed_150m = wind_resource_service.scale_wind_shear_power_law(ref_speed_120m, 150.0, 120.0, alpha=alpha)
    assert speed_150m > ref_speed_120m, "Wind at 150m must be higher than at 120m"


# ── TEST 3: POWER-CURVE INTERPOLATION & PHYSICAL BOUNDS ──────────────────────

def test_power_curve_interpolation_and_bounds():
    """Verify cut-in, below-rated, rated, cut-out, and generator capacity bounds."""
    # GE 2.5-120: Cut-in=3.0 m/s, Rated=11.5 m/s, Cut-out=25.0 m/s, Rated power=2500 kW
    p_zero, ct_zero = interpolate_turbine_power_and_ct("ge_25_120", 0.0)
    assert p_zero == 0.0

    p_below_cutin, _ = interpolate_turbine_power_and_ct("ge_25_120", 2.5)
    assert p_below_cutin == 0.0

    p_partial, ct_partial = interpolate_turbine_power_and_ct("ge_25_120", 8.0)
    assert 1400.0 <= p_partial <= 1650.0
    assert 0.70 <= ct_partial <= 0.85

    p_rated, ct_rated = interpolate_turbine_power_and_ct("ge_25_120", 12.0)
    assert p_rated == 2500.0, "Power at or above rated wind speed must be exactly 2500 kW"

    p_high, _ = interpolate_turbine_power_and_ct("ge_25_120", 20.0)
    assert p_high == 2500.0

    p_cutout, _ = interpolate_turbine_power_and_ct("ge_25_120", 26.0)
    assert p_cutout == 0.0, "Turbine must shut down above cut-out speed"

    # Invariant: Power is non-negative and strictly <= rated power
    for u in np.arange(0.0, 30.0, 0.5):
        p, _ = interpolate_turbine_power_and_ct("ge_25_120", float(u))
        assert p >= 0.0
        assert p <= 2500.0


# ── TEST 4: SINGLE-TURBINE FREESTREAM BASELINE ───────────────────────────────

def test_single_turbine_baseline_zero_wake_loss():
    """Verify an isolated single turbine experiences 0.0% wake loss and gross equals wake-adjusted."""
    single_pos = [{"id": "T1", "latitude": 14.6815, "longitude": 77.6005, "elevation_m": 45.0}]
    res = aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=single_pos,
        turbine_model_id="ge_25_120",
    )

    assert res.status in ("READY", "PARTIAL")
    assert res.turbine_count == 1
    assert res.wake_loss_pct == 0.0, "Single turbine must have exactly 0.0% wake loss"
    assert res.wake_adjusted_aep_gwh == res.gross_aep_gwh, "Gross AEP must equal Wake-Adjusted AEP for single turbine"
    assert res.net_aep_gwh < res.gross_aep_gwh, "Net AEP must be less than gross due to BoP technical losses"
    assert res.turbines[0].wake_deficit_pct == 0.0
    assert res.turbines[0].effective_speed_mps == res.turbines[0].freestream_speed_mps


# ── TEST 5: DOWNSTREAM WAKE DEFICIT (2 TURBINES) ──────────────────────────────

def test_two_turbines_downstream_wake_deficit():
    """Verify 2 in-line turbines produce measurable downstream velocity deficit."""
    engine = FlorisWakeEngine("ge_25_120")
    # T1 at origin, T2 at 600m East (5 diameters apart for D=120m)
    positions = [(0.0, 0.0), (600.0, 0.0)]

    # Wind arrives FROM West (270 deg) -> travels East
    res = engine.simulate_farm_wake(positions, wind_speed_mps=8.5, wind_direction_deg=270.0)

    u1 = res["effective_speeds"][0]
    u2 = res["effective_speeds"][1]
    def1 = res["wake_deficits_pct"][0]
    def2 = res["wake_deficits_pct"][1]

    assert u1 == 8.5, "Upstream turbine T1 must see full freestream"
    assert def1 == 0.0, "Upstream turbine T1 must have zero deficit"
    assert u2 < u1, "Downstream turbine T2 must experience reduced wind speed"
    assert def2 > 10.0, f"Downstream turbine T2 must have significant wake deficit, got {def2}%"
    assert res["instant_wake_loss_pct"] > 0.0


# ── TEST 6: CROSSWIND SEPARATION (LATERAL DECAY) ─────────────────────────────

def test_crosswind_separation_reduces_wake_interaction():
    """Verify increasing lateral separation reduces wake interaction."""
    engine = FlorisWakeEngine("ge_25_120")

    # Centerline downwind: T2 at (600m downwind, 0m lateral)
    res_center = engine.simulate_farm_wake([(0.0, 0.0), (600.0, 0.0)], wind_speed_mps=8.5, wind_direction_deg=270.0)
    # Lateral offset: T2 at (600m downwind, 150m lateral)
    res_offset = engine.simulate_farm_wake([(0.0, 0.0), (600.0, 150.0)], wind_speed_mps=8.5, wind_direction_deg=270.0)
    # Wide offset: T2 at (600m downwind, 400m lateral)
    res_wide = engine.simulate_farm_wake([(0.0, 0.0), (600.0, 400.0)], wind_speed_mps=8.5, wind_direction_deg=270.0)

    def_center = res_center["wake_deficits_pct"][1]
    def_offset = res_offset["wake_deficits_pct"][1]
    def_wide = res_wide["wake_deficits_pct"][1]

    assert def_offset < def_center, "Lateral offset must reduce wake deficit"
    assert def_wide < def_offset, "Wide lateral offset must further reduce wake deficit"
    assert def_wide < 1.0, "Wide separation outside Gaussian plume must approach 0 deficit"


# ── TEST 7: DOWNWIND SEPARATION (WAKE EXPANSION & CENTER RECOVERY) ───────────

def test_downwind_separation_causes_wake_deficit_recovery():
    """Verify wake deficit decays downwind as Gaussian plume expands."""
    engine = FlorisWakeEngine("ge_25_120")

    # Deficit at 4D (480m) vs 8D (960m) vs 12D (1440m)
    def_4d = engine.calculate_gaussian_wake_deficit(downwind_x_m=480.0, crosswind_r_m=0.0, ct=0.8)
    def_8d = engine.calculate_gaussian_wake_deficit(downwind_x_m=960.0, crosswind_r_m=0.0, ct=0.8)
    def_12d = engine.calculate_gaussian_wake_deficit(downwind_x_m=1440.0, crosswind_r_m=0.0, ct=0.8)

    assert def_8d < def_4d, "Deficit at 8D must be less than at 4D due to wake recovery"
    assert def_12d < def_8d, "Deficit at 12D must be less than at 8D due to further recovery"


# ── TEST 8: DIRECTION CHANGES & REVERSAL ─────────────────────────────────────

def test_direction_reversal_swaps_upstream_and_downstream_roles():
    """Verify changing wind direction by 180 degrees swaps which turbine is wake-affected."""
    engine = FlorisWakeEngine("ge_25_120")
    positions = [(0.0, 0.0), (600.0, 0.0)]  # T1 at 0m, T2 at 600m East

    # Wind FROM West (270 deg) -> T1 upstream, T2 waked
    res_west = engine.simulate_farm_wake(positions, wind_speed_mps=8.5, wind_direction_deg=270.0)
    assert res_west["wake_deficits_pct"][0] == 0.0
    assert res_west["wake_deficits_pct"][1] > 10.0

    # Wind FROM East (90 deg) -> T2 upstream, T1 waked
    res_east = engine.simulate_farm_wake(positions, wind_speed_mps=8.5, wind_direction_deg=90.0)
    assert res_east["wake_deficits_pct"][1] == 0.0
    assert res_east["wake_deficits_pct"][0] > 10.0


# ── TEST 9: AIR DENSITY HANDLING & NORMALIZATION ─────────────────────────────

def test_air_density_normalization():
    """Verify air density affects below-rated power per IEC 61400-12-1 and caps at rated."""
    # Low density (e.g. high altitude: rho = 1.05 kg/m3)
    p_low, _ = interpolate_turbine_power_and_ct("ge_25_120", wind_speed_mps=8.0, air_density_kgm3=1.05)
    # Standard sea level density (rho = 1.225 kg/m3)
    p_std, _ = interpolate_turbine_power_and_ct("ge_25_120", wind_speed_mps=8.0, air_density_kgm3=1.225)
    # High density (cold sea level: rho = 1.28 kg/m3)
    p_high, _ = interpolate_turbine_power_and_ct("ge_25_120", wind_speed_mps=8.0, air_density_kgm3=1.28)

    assert p_low < p_std < p_high, "Below-rated power must increase monotonically with air density"

    # Both must clamp at generator rated capacity at high wind speeds
    p_rated_low, _ = interpolate_turbine_power_and_ct("ge_25_120", wind_speed_mps=13.0, air_density_kgm3=1.05)
    p_rated_high, _ = interpolate_turbine_power_and_ct("ge_25_120", wind_speed_mps=13.0, air_density_kgm3=1.28)
    assert p_rated_low == 2500.0
    assert p_rated_high == 2500.0

    # Barometric elevation calculation test
    rho_sea = wind_resource_service.calculate_barometric_air_density(0.0)
    rho_1000m = wind_resource_service.calculate_barometric_air_density(1000.0)
    assert rho_sea == 1.225
    assert rho_1000m < rho_sea


# ── TEST 10: LOSS ACCOUNTING (IEC 61400-15) ──────────────────────────────────

def test_loss_accounting_breakdown():
    """Verify explicit accounting of electrical, availability, curtailment, environmental, and hysteresis losses."""
    positions = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 45.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 45.0},
    ]

    res = aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=positions,
        turbine_model_id="ge_25_120",
    )

    losses = res.losses
    assert losses.electrical_loss_pct == 2.5
    assert losses.availability_loss_pct == 3.0
    assert losses.curtailment_loss_pct == 1.5
    assert losses.environmental_loss_pct == 1.5
    assert losses.hysteresis_loss_pct == 1.5
    assert 9.0 <= losses.total_bop_loss_pct <= 10.5
    assert 0.89 <= losses.net_energy_derate_factor <= 0.91

    # Invariant: Net AEP = Wake-Adjusted AEP * net_energy_derate_factor
    expected_net = round(res.wake_adjusted_aep_gwh * losses.net_energy_derate_factor, 2)
    assert abs(res.net_aep_gwh - expected_net) <= 0.05


# ── TEST 11: MISSING-RESOURCE UNKNOWN / UNAVAILABLE PROPAGATION ───────────────

def test_missing_resource_unknown_propagation():
    """Verify missing or failed wind resource returns UNKNOWN without synthetic numbers."""
    from backend.app.engineering.wind_resource_service import WindResourceRecord

    # Create unindexed/unknown wind record
    unknown_wind = WindResourceRecord(
        status="UNKNOWN",
        latitude=0.0,
        longitude=0.0,
        hub_height_m=110.0,
        retrieved_at="2026-10-07T00:00:00Z",
    )

    positions = [{"id": "T1", "latitude": 0.0, "longitude": 0.0}]
    res = aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=positions,
        turbine_model_id="ge_25_120",
        wind_resource=unknown_wind,
    )

    assert res.status == "UNKNOWN"
    assert res.gross_aep_gwh == 0.0
    assert res.net_aep_gwh == 0.0
    assert "UNKNOWN" in res.diagnostic_note


# ── TEST 12: DETERMINISM OF IDENTICAL CALCULATIONS ───────────────────────────

def test_deterministic_aep_calculations():
    """Verify repeated evaluations with identical inputs produce identical results."""
    positions = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 45.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 45.0},
        {"id": "T3", "latitude": 14.690, "longitude": 77.610, "elevation_m": 45.0},
    ]

    res1 = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="ge_25_120")
    res2 = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="ge_25_120")

    assert res1.gross_aep_gwh == res2.gross_aep_gwh
    assert res1.wake_adjusted_aep_gwh == res2.wake_adjusted_aep_gwh
    assert res1.net_aep_gwh == res2.net_aep_gwh
    assert res1.wake_loss_pct == res2.wake_loss_pct


# ── TEST 13: TURBINE MODEL DIFFERENTIATION ───────────────────────────────────

def test_different_turbine_models_produce_different_physical_results():
    """Verify changing turbine model changes rated power, energy yield, and wake losses."""
    positions = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 45.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 45.0},
    ]

    res_ge = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="ge_25_120")
    res_vestas = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="vestas_v110_20")
    res_nrel = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="nrel_5mw")

    # Capacities must reflect catalogue
    assert res_ge.total_rated_capacity_mw == 5.0    # 2 x 2.5 MW
    assert res_vestas.total_rated_capacity_mw == 4.0  # 2 x 2.0 MW
    assert res_nrel.total_rated_capacity_mw == 10.0   # 2 x 5.0 MW

    # Yields must be distinctly different
    assert res_vestas.net_aep_gwh < res_ge.net_aep_gwh < res_nrel.net_aep_gwh


# ── TEST 14: REAL ANANTAPUR END-TO-END INTEGRATION TEST ──────────────────────

def test_real_data_sample_anantapur_aep_integration():
    """Test full integration chain on checked-in Anantapur real dataset."""
    assert SAMPLE_PATH.exists()
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    # Generate feasible candidates using Phase 4 engine
    from backend.app.engineering.candidate_engine import candidate_engine
    p4_gen = candidate_engine.generate_candidates(
        search_envelope_geometry=data["boundary"]["geometry"],
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=10,
    )

    assert p4_gen.feasible_count >= 5
    candidates = p4_gen.feasible_candidates[:8]

    # Evaluate preliminary AEP on these real candidates
    cand_dicts = [
        {
            "id": c.candidate_id,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "utm_easting_m": c.utm_easting_m,
            "utm_northing_m": c.utm_northing_m,
            "elevation_m": c.elevation_m or 347.0,
        }
        for c in candidates
    ]

    aep_res = aep_calculation_engine.evaluate_layout_aep(
        candidate_positions=cand_dicts,
        turbine_model_id="ge_25_120",
        site_elevation_m=347.0,
    )

    assert aep_res.status in ("READY", "PARTIAL")
    assert aep_res.turbine_count == len(candidates)
    assert aep_res.total_rated_capacity_mw == len(candidates) * 2.5
    assert aep_res.gross_aep_gwh > 0.0
    assert aep_res.wake_adjusted_aep_gwh > 0.0
    assert aep_res.net_aep_gwh > 0.0
    assert aep_res.wake_loss_pct >= 0.0
    assert 20.0 <= aep_res.net_capacity_factor_pct <= 45.0
    assert aep_res.wind_resource_source is not None
    assert aep_res.provenance is not None


# ── TEST 15: ENGINEERING PHYSICAL SANITY GUARDS ──────────────────────────────

def test_engineering_physical_sanity_guards():
    """Verify physical sanity guard rejects impossible values (AEP > max, negative power, etc.)."""
    positions = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "elevation_m": 45.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "elevation_m": 45.0},
    ]

    res = aep_calculation_engine.evaluate_layout_aep(positions, turbine_model_id="ge_25_120")

    # Invariants
    theoretical_max = res.total_rated_capacity_mw * 8.76
    assert res.gross_aep_gwh <= theoretical_max
    assert res.net_aep_gwh <= res.wake_adjusted_aep_gwh <= res.gross_aep_gwh
    assert res.net_capacity_factor_pct <= 100.0
    assert res.gross_capacity_factor_pct <= 100.0

    for node in res.turbines:
        assert node.effective_speed_mps <= node.freestream_speed_mps
        assert node.net_energy_mwh >= 0.0
        assert node.gross_energy_mwh >= 0.0


# ── TEST 16: MACHINE-READABLE PHASE 6 PERFORMANCE CONTRACT ───────────────────

def test_phase6_performance_contract():
    """Verify machine-readable contract exposed for Phase 6 QUBO/QAOA."""
    candidates = [
        {"id": "C1", "latitude": 14.680, "longitude": 77.600},
        {"id": "C2", "latitude": 14.685, "longitude": 77.605},
        {"id": "C3", "latitude": 14.690, "longitude": 77.610},
    ]

    contract = aep_calculation_engine.build_phase6_performance_contract(
        candidate_positions=candidates,
        turbine_model_id="ge_25_120",
    )

    assert contract["contract_version"] == "1.0.0"
    assert contract["candidate_count"] == 3
    assert len(contract["candidate_ids"]) == 3
    assert len(contract["linear_objective_coeffs"]) == 3
    assert all(c > 0.0 for c in contract["linear_objective_coeffs"])

    # Quadratic wake penalty matrix Q_ij
    Q = np.array(contract["quadratic_wake_penalty_matrix"])
    assert Q.shape == (3, 3)
    assert np.all(np.diag(Q) == 0.0), "Self-wake on diagonal must be zero"
    assert np.all(Q >= 0.0), "Wake penalties must be non-negative"


# ── TEST 17: FASTAPI ENGINEERING ENDPOINTS INTEGRATION ───────────────────────

def test_fastapi_wind_wake_aep_endpoints():
    """Verify HTTP endpoints for wind climatology, power curve, wake simulation, and AEP."""
    # 1. Climatology endpoint
    res_clim = client.get("/api/engineering/wind/climatology?lat=14.6815&lon=77.6005&hub_height_m=110.0")
    assert res_clim.status_code == 200
    clim_data = res_clim.json()
    assert clim_data["status"] in ("READY", "PARTIAL")
    assert clim_data["annual_mean_wind_speed_mps"] > 5.0
    assert len(clim_data["wind_rose_16"]) == 16

    # 2. Power curve endpoint
    res_curve = client.post(
        "/api/engineering/turbines/power-curve",
        json={"turbine_model_id": "ge_25_120", "air_density_kgm3": 1.225},
    )
    assert res_curve.status_code == 200
    curve_data = res_curve.json()
    assert len(curve_data["curve_points"]) == 26
    assert curve_data["rated_power_kw"] == 2500.0

    # 3. Wake simulate endpoint
    res_wake = client.post(
        "/api/engineering/wake/simulate",
        json={
            "positions": [{"east_m": 0.0, "north_m": 0.0}, {"east_m": 600.0, "north_m": 0.0}],
            "turbine_model_id": "ge_25_120",
            "wind_speed_mps": 8.5,
            "wind_direction_from_deg": 270.0,
        },
    )
    assert res_wake.status_code == 200
    wake_data = res_wake.json()
    assert wake_data["wind_to_deg"] == 90.0
    assert wake_data["wake_deficits_pct"][1] > 0.0

    # 4. AEP evaluate endpoint
    res_aep = client.post(
        "/api/engineering/aep/evaluate",
        json={
            "candidate_positions": [{"lat": 14.680, "lon": 77.600}, {"lat": 14.685, "lon": 77.605}],
            "turbine_model_id": "ge_25_120",
            "site_elevation_m": 45.0,
        },
    )
    assert res_aep.status_code == 200
    aep_data = res_aep.json()
    assert aep_data["gross_aep_gwh"] > 0.0
    assert aep_data["net_aep_gwh"] > 0.0
    assert aep_data["losses"]["total_bop_loss_pct"] > 0.0

    # 5. Phase 6 contract endpoint
    res_contract = client.post(
        "/api/engineering/aep/phase6-contract",
        json={
            "candidate_positions": [{"lat": 14.680, "lon": 77.600}, {"lat": 14.685, "lon": 77.605}],
            "turbine_model_id": "ge_25_120",
        },
    )
    assert res_contract.status_code == 200
    c_data = res_contract.json()
    assert "quadratic_wake_penalty_matrix" in c_data

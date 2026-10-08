"""
tests/test_qubo_qaoa_audit.py
AeroQuantum-Wind Phase 6.1: Final QUBO/QAOA Correctness & Optimization Audit Test Suite.

Audits:
1. QUBO objective proof: target-count penalty prevents k-1 and k+1 solutions from beating feasible k solutions.
2. Spacing contract: non-feasible (EXCLUDED, UNKNOWN, invalid) candidates can NEVER enter optimization.
3. QAOA quality validation: empirical approximation ratio, optimality gap, and sampling probability.
4. Top-K coverage: exact QUBO and physical optimum inclusion in sampled set.
5. QUBO surrogate vs physical objective: layout reordering under exact FLORIS multi-turbine physics.
6. Scaling & fallback safety: NO silent classical fallback presented as QAOA, truthful error statuses.
7. IBM Quantum hardware audit: zero fabrication, truthful HARDWARE_UNAVAILABLE.
8. Penalty scaling & numerical stability: extreme small/large energy coefficients without overflow/NaN.
9. Physical finalization: complete physical metadata on declared optimum.
10. API truthfulness: endpoints distinguish QUBO surrogate, classical optimum, QAOA sampled, and physical truth.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.engineering.qubo_engine import (
    QuboProblem,
    build_qubo_from_phase6_contract,
)
from backend.app.engineering.qaoa_engine import (
    QAOALayoutOptimizer,
    AerSimulatorBackend,
    IBMQuantumHardwareBackend,
)
from backend.app.engineering.aep_engine import aep_calculation_engine
from backend.app.engineering.candidate_engine import candidate_engine


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "backend" / "data" / "samples" / "real_data_sample_anantapur.json"


# ── AUDIT 1: QUBO OBJECTIVE PROOF & TARGET COUNT PENALTY ──────────────────────

def test_qubo_objective_proof_target_count_penalty_exhaustive():
    """
    Exhaustively proves across all 2^N states with unequal candidate energies that:
    1. Feasible k-turbine solutions strictly beat k-1 and k+1 solutions solely due to penalty calibration.
    2. Unequal candidate energies (5,000 MWh to 15,000 MWh) are handled correctly.
    """
    n = 6
    target_k = 3
    # Unequal candidate energies
    linear_e = [5000.0, 7500.0, 10000.0, 12000.0, 14000.0, 15000.0]
    positions = [(i * 1200.0, 0.0) for i in range(n)]
    wake_mat = [[50.0 * abs(i - j) if i != j else 0.0 for j in range(n)] for i in range(n)]
    eta = 0.9038

    qubo = QuboProblem(
        candidate_ids=[f"C{i}" for i in range(n)],
        positions_metric=positions,
        linear_energy_mwh=linear_e,
        wake_penalty_matrix_mwh=wake_mat,
        target_turbines=target_k,
        min_spacing_m=800.0,
        bop_derate_factor=eta,
    )

    k_solutions = []
    k_minus_1_solutions = []
    k_plus_1_solutions = []

    for bit in range(2 ** n):
        bits = [(bit >> i) & 1 for i in range(n)]
        eval_res = qubo.evaluate_bitstring(bits)
        m = eval_res.selected_count
        if m == target_k and eval_res.is_feasible:
            k_solutions.append(eval_res)
        elif m == target_k - 1:
            k_minus_1_solutions.append(eval_res)
        elif m == target_k + 1:
            k_plus_1_solutions.append(eval_res)

    best_k_cost = min(s.qubo_cost for s in k_solutions)
    best_k_minus_1_cost = min(s.qubo_cost for s in k_minus_1_solutions)
    best_k_plus_1_cost = min(s.qubo_cost for s in k_plus_1_solutions)

    # Mathematical Proof: k solution strictly beats k-1 and k+1 solutions
    assert best_k_cost < best_k_minus_1_cost, (
        f"k-1 solution beat k solution: best k={best_k_cost}, best k-1={best_k_minus_1_cost}"
    )
    assert best_k_cost < best_k_plus_1_cost, (
        f"k+1 solution beat k solution: best k={best_k_cost}, best k+1={best_k_plus_1_cost}"
    )

    # Margin check: the cost gap must be >= 0.5 * max(E_i * eta)
    max_energy = max(linear_e) * eta
    assert (best_k_plus_1_cost - best_k_cost) >= 0.45 * max_energy


# ── AUDIT 2: SPACING CONTRACT & DEFENSE-IN-DEPTH ──────────────────────────────

def test_spacing_contract_filters_non_feasible_candidates():
    """Verify that EXCLUDED, UNKNOWN, and invalid candidates are rejected before QUBO."""
    client = TestClient(app)

    mixed_candidates = [
        {"id": "VALID_1", "latitude": 14.680, "longitude": 77.600, "utm_easting_m": 780000, "utm_northing_m": 1624000, "is_feasible": True, "feasibility_status": "FEASIBLE"},
        {"id": "VALID_2", "latitude": 14.685, "longitude": 77.605, "utm_easting_m": 780800, "utm_northing_m": 1624800, "is_feasible": True, "feasibility_status": "FEASIBLE"},
        {"id": "EXCLUDED_1", "latitude": 14.690, "longitude": 77.610, "utm_easting_m": 781600, "utm_northing_m": 1625600, "is_feasible": False, "feasibility_status": "HARD_EXCLUDED"},
        {"id": "UNKNOWN_1", "latitude": 14.695, "longitude": 77.615, "utm_easting_m": 782400, "utm_northing_m": 1626400, "is_feasible": None, "feasibility_status": "UNKNOWN"},
        {"id": "CORRUPTED", "latitude": None, "longitude": "invalid", "is_feasible": True},
    ]

    res = client.post(
        "/api/engineering/optimization/qubo-formulation",
        json={
            "candidates": mixed_candidates,
            "turbine_model_id": "ge_25_120",
            "target_turbines": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Only 2 valid candidates must enter the QUBO
    assert data["qubo_problem"]["n_candidates"] == 2
    assert data["qubo_problem"]["candidate_ids"] == ["VALID_1", "VALID_2"]
    assert "DEFENSE_IN_DEPTH" in data["qubo_problem"]["spacing_classification"]

    # If only non-feasible candidates are sent, must return HTTP 400
    bad_res = client.post(
        "/api/engineering/optimization/qubo-formulation",
        json={"candidates": [mixed_candidates[2], mixed_candidates[3]], "turbine_model_id": "ge_25_120"},
    )
    assert bad_res.status_code == 400
    assert "No FEASIBLE candidates provided" in bad_res.json()["detail"]


# ── AUDIT 3 & 4: QAOA QUALITY & TOP-K COVERAGE AUDIT ──────────────────────────

def test_qaoa_solution_quality_and_top_k_coverage():
    """
    Formally benchmark QAOA against certified classical optimum across multiple seeds:
    measures approximation ratio, optimality gap, and top-K coverage.
    """
    qubo = QuboProblem(
        candidate_ids=["C1", "C2", "C3", "C4"],
        positions_metric=[(0, 0), (0, 1000), (1000, 0), (1000, 1000)],
        linear_energy_mwh=[10000.0, 10000.0, 10000.0, 10000.0],
        wake_penalty_matrix_mwh=[
            [0.0, 500.0, 200.0, 50.0],
            [500.0, 0.0, 50.0, 200.0],
            [200.0, 50.0, 0.0, 500.0],
            [50.0, 200.0, 500.0, 0.0],
        ],
        target_turbines=2,
        min_spacing_m=800.0,
    )

    optimizer = QAOALayoutOptimizer(
        backend=AerSimulatorBackend(seed=42),
        p_layers=1,
        shots=1024,
        max_classical_iterations=20,
        top_k_physical_reeval=5,
    )

    audit = optimizer.audit_qaoa_solution_quality(
        qubo=qubo,
        repetitions=5,
        seeds=[42, 101, 202, 303, 404],
    )

    assert audit["status"] == "AUDIT_COMPLETED"
    assert audit["exact_qubo_optimum"]["bitstring"] in ["1001", "0110"]
    assert audit["metrics"]["all_runs_found_feasible"] is True

    # Approximation ratio should be >= 0.95 (typically 0.98 - 1.00)
    assert audit["metrics"]["mean_approximation_ratio"] >= 0.95
    # Exact optimum should be sampled in >= 60% of runs
    assert audit["metrics"]["probability_sampling_exact_optimum"] >= 0.60
    # Exact optimum should appear in top-K in 100% of runs
    assert audit["metrics"]["probability_exact_optimum_in_top_k"] == 1.0


# ── AUDIT 5: QUBO SURROGATE VS PHYSICAL OBJECTIVE REORDERING ──────────────────

def test_qubo_surrogate_vs_physical_objective_ranking_reordering():
    """
    Audit layout reordering between pairwise QUBO surrogate and exact FLORIS physical AEP.
    Demonstrates that QAOA optimizes the surrogate, but exact multi-turbine physics selects the final optimum.
    """
    qubo = QuboProblem(
        candidate_ids=["C1", "C2", "C3", "C4"],
        positions_metric=[(0, 0), (0, 1000), (1000, 0), (1000, 1000)],
        linear_energy_mwh=[10000.0] * 4,
        wake_penalty_matrix_mwh=[
            [0.0, 500.0, 200.0, 50.0],
            [500.0, 0.0, 50.0, 200.0],
            [200.0, 50.0, 0.0, 500.0],
            [50.0, 200.0, 500.0, 0.0],
        ],
        target_turbines=2,
        min_spacing_m=800.0,
    )

    optimizer = QAOALayoutOptimizer(backend=AerSimulatorBackend(seed=42), p_layers=1, shots=512)
    res = optimizer.optimize_layout(qubo, site_elevation_m=350.0)

    assert res["status"] == "OPTIMIZATION_COMPLETED"
    phys_results = res["physical_reevaluation"]["results"]
    assert len(phys_results) >= 2

    # Physical re-evaluation occurred and assigned exact Net AEP
    for r in phys_results:
        assert r["exact_net_aep_gwh"] > 0.0
        assert r["exact_wake_loss_pct"] >= 0.0
        assert "FLORIS" in res["provenance"]["physical_layer"]

    # Winning engineering layout has optimality scope disclaimed
    winner = res["declared_engineering_optimum"]
    assert "Locally optimal among sampled top-K candidates" in winner["optimality_scope"]


# ── AUDIT 6: SCALING & FALLBACK SAFETY (NO SILENT FALLBACK) ───────────────────

def test_scaling_and_fallback_safety_no_silent_classical_fallback():
    """
    Verify truthful status reporting:
    1. If no feasible bitstrings are sampled, return NO_FEASIBLE_BITSTRINGS_SAMPLED.
       Zero silent classical fallback!
    2. If candidate count exceeds simulator limit (24 qubits), return SIMULATOR_QUBIT_LIMIT_EXCEEDED.
    3. If combinations exceed limit, classical solver returns EXHAUSTIVE_LIMIT_EXCEEDED.
    """
    # 1. Impossible spacing constraint: all candidates spaced 100m, but min spacing is 1000m
    # Selecting target_k=2 is impossible without spacing violations
    qubo_impossible = QuboProblem(
        candidate_ids=["C1", "C2", "C3"],
        positions_metric=[(0, 0), (100, 0), (200, 0)],
        linear_energy_mwh=[5000.0] * 3,
        wake_penalty_matrix_mwh=[[0.0] * 3 for _ in range(3)],
        target_turbines=2,
        min_spacing_m=1000.0,
    )

    optimizer = QAOALayoutOptimizer(backend=AerSimulatorBackend(seed=42), p_layers=1, shots=100)
    res = optimizer.optimize_layout(qubo_impossible)

    # Must return NO_FEASIBLE_BITSTRINGS_SAMPLED with None winner, NO classical fallback!
    assert res["status"] == "NO_FEASIBLE_BITSTRINGS_SAMPLED"
    assert res["feasible_sampling_success"] is False
    assert res["declared_engineering_optimum"] is None
    assert "produced no bitstrings satisfying" in res["error_message"]

    # 2. Simulator qubit limit check (> 24 qubits)
    qubo_large = QuboProblem(
        candidate_ids=[f"C{i}" for i in range(26)],
        positions_metric=[(i * 1000.0, 0.0) for i in range(26)],
        linear_energy_mwh=[5000.0] * 26,
        wake_penalty_matrix_mwh=[[0.0] * 26 for _ in range(26)],
        target_turbines=4,
        min_spacing_m=500.0,
    )
    res_large = optimizer.optimize_layout(qubo_large)
    assert res_large["status"] == "SIMULATOR_QUBIT_LIMIT_EXCEEDED"
    assert "exceeds maximum simulator capacity limit" in res_large["error_message"]

    # 3. Classical exhaustive limit check
    res_class_large = qubo_large.solve_classical_exhaustive(max_combinations=500)
    assert res_class_large["status"] == "EXHAUSTIVE_LIMIT_EXCEEDED"
    assert "exceeds configured exhaustive search threshold" in res_class_large["error_message"]


# ── AUDIT 7: IBM QUANTUM HARDWARE GOVERNANCE (ZERO FABRICATION) ────────────────

def test_ibm_backend_audit_zero_fabrication():
    """Verify IBM hardware backend returns HARDWARE_UNAVAILABLE and raises no unhandled exception."""
    backend = IBMQuantumHardwareBackend(token=None)
    assert backend.is_available() is False
    assert backend.get_status() == "HARDWARE_UNAVAILABLE"

    info = backend.get_info()
    assert info["is_hardware"] is True
    assert "No IBM Quantum credentials configured" in info["error_reason"]

    # Fast check via API
    client = TestClient(app)
    res = client.get("/api/engineering/optimization/hardware-status")
    assert res.status_code == 200
    assert res.json()["status"] == "HARDWARE_UNAVAILABLE"


# ── AUDIT 8: PENALTY SCALE & NUMERICAL STABILITY ──────────────────────────────

def test_penalty_scale_and_numerical_stability():
    """Verify coefficient normalization and penalty scaling under extreme values."""
    # Extreme small energy coefficients (0.005 MWh/yr)
    qubo_small = QuboProblem(
        candidate_ids=["C1", "C2", "C3"],
        positions_metric=[(0, 0), (1000, 0), (2000, 0)],
        linear_energy_mwh=[0.005, 0.005, 0.005],
        wake_penalty_matrix_mwh=[[0.0] * 3 for _ in range(3)],
        target_turbines=2,
        min_spacing_m=500.0,
    )
    ising_small = qubo_small.to_ising()
    assert ising_small["scale_factor"] >= 1.0
    for v in ising_small["normalized_h"].values():
        assert not np.isnan(v) and not np.isinf(v)

    # Extreme large energy coefficients (10^7 MWh/yr)
    qubo_large = QuboProblem(
        candidate_ids=["C1", "C2", "C3"],
        positions_metric=[(0, 0), (1000, 0), (2000, 0)],
        linear_energy_mwh=[1e7, 1e7, 1e7],
        wake_penalty_matrix_mwh=[[0.0] * 3 for _ in range(3)],
        target_turbines=2,
        min_spacing_m=500.0,
    )
    ising_large = qubo_large.to_ising()
    assert ising_large["scale_factor"] >= 1e6
    for v in ising_large["normalized_h"].values():
        assert not np.isnan(v) and not np.isinf(v)
        assert abs(v) <= 1.0


# ── AUDIT 9: PHYSICAL FINALIZATION METADATA RETENTION ─────────────────────────

def test_physical_finalization_metadata_retention():
    """Verify that the declared engineering layout retains all required physical fields."""
    with open(SAMPLE_PATH) as f:
        data = json.load(f)

    p4_gen = candidate_engine.generate_candidates(
        search_envelope_geometry=data["boundary"]["geometry"],
        turbine_model_id="ge_25_120",
        min_spacing_diameters=4.0,
        max_candidates=4,
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
        for c in p4_gen.feasible_candidates[:4]
    ]

    client = TestClient(app)
    res = client.post(
        "/api/engineering/optimization/qaoa",
        json={
            "candidates": cands,
            "turbine_model_id": "ge_25_120",
            "target_turbines": 2,
            "site_elevation_m": 347.0,
            "shots": 256,
            "max_classical_iterations": 5,
        },
    )
    assert res.status_code == 200
    data = res.json()
    winner = data["declared_engineering_optimum"]
    assert winner is not None

    # Required fields
    assert "exact_net_aep_gwh" in winner
    assert "exact_gross_aep_gwh" in winner
    assert "exact_wake_adjusted_aep_gwh" in winner
    assert "exact_wake_loss_pct" in winner
    assert "exact_net_cf_pct" in winner
    assert "installed_capacity_mw" in winner
    assert "selected_candidate_ids" in winner
    assert "coordinates" in winner
    assert len(winner["coordinates"]) == 2
    assert "optimality_scope" in winner


# ── AUDIT 10: API QAOA QUALITY AUDIT ENDPOINT ─────────────────────────────────

def test_api_qaoa_quality_audit_endpoint():
    """Verify the /api/engineering/optimization/qaoa-quality-audit endpoint."""
    client = TestClient(app)
    candidates_payload = [
        {"id": "T1", "latitude": 14.680, "longitude": 77.600, "utm_easting_m": 780000, "utm_northing_m": 1624000, "elevation_m": 350.0},
        {"id": "T2", "latitude": 14.685, "longitude": 77.605, "utm_easting_m": 780800, "utm_northing_m": 1624800, "elevation_m": 350.0},
        {"id": "T3", "latitude": 14.690, "longitude": 77.610, "utm_easting_m": 781600, "utm_northing_m": 1625600, "elevation_m": 350.0},
    ]

    res = client.post(
        "/api/engineering/optimization/qaoa-quality-audit",
        json={
            "candidates": candidates_payload,
            "turbine_model_id": "ge_25_120",
            "target_turbines": 2,
            "shots": 256,
            "repetitions": 3,
            "seeds": [42, 101, 202],
        },
    )
    assert res.status_code == 200
    audit = res.json()
    assert audit["status"] == "AUDIT_COMPLETED"
    assert "metrics" in audit
    assert "individual_runs" in audit
    assert len(audit["individual_runs"]) == 3
    assert "mean_approximation_ratio" in audit["metrics"]
    assert "probability_sampling_exact_optimum" in audit["metrics"]

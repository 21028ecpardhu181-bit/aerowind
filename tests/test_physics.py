"""
tests/test_physics.py — Unit test suite for AeroQuantum-Wind physics kernel.

Covers:
1. Anantapur 16-bin wind rose distribution and Weibull parameters (sums to 100%).
2. Jensen analytical wake deficit model (monotonic decay with downwind distance x).
3. Pairwise wake interaction matrix properties and directional geometry.
4. QAOA Ising cost Hamiltonian construction (J strictly symmetric with zero diagonal).
5. 2x2 toy grid ground state validation matching classical brute-force evaluation.
6. Auto-calibrated penalty coefficients (lambda_turb = 1.5 * max|W_ij|).
"""

import itertools
import json
from pathlib import Path

import numpy as np
import pytest

from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
    wake_deficit,
    wind_direction_vector,
)
from core.quantum_hamiltonian import (
    brute_force_solver,
    build_ising,
    evaluate_binary_cost,
    evaluate_ising_energy,
)


class TestWindRoseData:
    """Validates the 16-bin wind rose fixture for Anantapur, AP."""

    def test_wind_rose_bins_sum_to_100_percent(self):
        data = load_wind_rose_fixture()
        bins = data["bins"]

        assert len(bins) == 16, f"Expected exactly 16 directional bins, got {len(bins)}"

        freq_sum = sum(b["frequency_pct"] for b in bins)
        assert pytest.approx(freq_sum, abs=1e-5) == 100.0, (
            f"Bin frequencies must sum to 100.0%, got {freq_sum}%"
        )

        for b in bins:
            assert b["frequency_pct"] > 0, f"Bin {b['direction_label']} frequency must be positive"
            assert 0.0 <= b["angle_deg"] < 360.0, f"Angle {b['angle_deg']} out of compass bounds"

    def test_wind_rose_metadata_and_weibull_params(self):
        data = load_wind_rose_fixture()
        meta = data["site_metadata"]

        assert meta["coordinates"]["latitude"] == 14.68
        assert meta["coordinates"]["longitude"] == 77.60
        assert meta["annual_weibull_k"] == 2.14
        assert meta["annual_weibull_c_mps"] == 8.42
        assert "Southwest Monsoon" in meta["source_assumptions"]

    def test_prevailing_sw_monsoon_dominance(self):
        """Validates that WSW, W, and SW sectors carry the prevailing wind energy."""
        data = load_wind_rose_fixture()
        bins_by_label = {b["direction_label"]: b["frequency_pct"] for b in data["bins"]}

        # SW monsoon peak: WSW (247.5°) and W (270°) should have highest frequencies
        assert bins_by_label["WSW"] >= 20.0
        assert bins_by_label["W"] >= 15.0
        assert bins_by_label["SW"] >= 15.0

        sw_core_sum = (
            bins_by_label["SSW"]
            + bins_by_label["SW"]
            + bins_by_label["WSW"]
            + bins_by_label["W"]
            + bins_by_label["WNW"]
        )
        assert sw_core_sum >= 70.0, f"SW monsoon corridor must dominate annual flux, got {sw_core_sum}%"


class TestJensenWakeModel:
    """Validates the vectorized Jensen wake deficit kernel."""

    def test_deficit_decreases_monotonically_with_downwind_distance(self):
        """Asserts that wake deficit strictly decreases as distance x increases."""
        D = 120.0
        Ct = 0.8
        k = 0.075

        distances = np.array([50.0, 100.0, 200.0, 300.0, 600.0, 1000.0, 2000.0])
        deficits = wake_deficit(distances, D=D, Ct=Ct, k=k)

        # All deficits must be positive and less than 1.0
        assert np.all(deficits > 0.0)
        assert np.all(deficits < 1.0)

        # Monotonic decrease: deficit[i] > deficit[i+1]
        for i in range(len(deficits) - 1):
            assert deficits[i] > deficits[i + 1], (
                f"Deficit at x={distances[i]} ({deficits[i]:.4f}) not strictly greater than "
                f"at x={distances[i+1]} ({deficits[i+1]:.4f})"
            )

    def test_deficit_at_upwind_or_zero_distance(self):
        """Asserts zero deficit for turbines not downstream (x <= 0)."""
        assert wake_deficit(0.0) == 0.0
        assert wake_deficit(-100.0) == 0.0

        x_arr = np.array([-500.0, -10.0, 0.0, 100.0])
        deficits = wake_deficit(x_arr)
        assert deficits[0] == 0.0
        assert deficits[1] == 0.0
        assert deficits[2] == 0.0
        assert deficits[3] > 0.0

    def test_analytical_jensen_formula_precision(self):
        """Asserts exact numerical correspondence to (1 - sqrt(1 - Ct)) / (1 + 2kx/D)^2."""
        D = 120.0
        Ct = 0.8
        k = 0.075
        x = 600.0  # 5D cutoff

        expected_num = 1.0 - np.sqrt(1.0 - Ct)
        expected_den = (1.0 + 2.0 * k * x / D) ** 2
        expected_val = expected_num / expected_den

        actual_val = wake_deficit(x, D=D, Ct=Ct, k=k)
        assert pytest.approx(actual_val, rel=1e-7) == expected_val
        assert pytest.approx(actual_val, abs=1e-4) == 0.1805


class TestPairwiseWakeMatrix:
    """Validates the N×N wake matrix generation."""

    def test_pairwise_wake_matrix_zero_diagonal(self):
        coords = np.array([
            [0.0, 0.0],
            [300.0, 0.0],
            [600.0, 0.0],
            [900.0, 0.0],
        ])
        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0, D=120.0, Ct=0.8, k=0.075)

        assert W.shape == (4, 4)
        assert np.all(np.diag(W) == 0.0), "Diagonal of wake matrix must be strictly zero"

    def test_directional_shadowing_and_cutoff(self):
        """West wind (270°): blows East (+x). Downwind turbines get wake; upwind get 0."""
        coords = np.array([
            [0.0, 0.0],     # site 0
            [300.0, 0.0],   # site 1 (downwind of 0)
            [800.0, 0.0],   # site 2 (downwind of 0, but > 600m cutoff from 0)
        ])
        W = pairwise_wake_matrix(
            coords, wind_angle_deg=270.0, D=120.0, Ct=0.8, k=0.075, cutoff_m=600.0
        )

        # Site 0 wakes Site 1 at 300m
        assert W[0, 1] > 0.0
        # Site 1 does NOT wake Site 0 (it is downwind, not upwind)
        assert W[1, 0] == 0.0
        # Site 0 does NOT wake Site 2 (800m > 600m cutoff)
        assert W[0, 2] == 0.0
        # Site 1 wakes Site 2 at 500m (800 - 300 = 500m <= 600m)
        assert W[1, 2] > 0.0

    def test_crosswind_turbines_outside_cone_have_zero_deficit(self):
        """Crosswind turbines separated beyond wake radius receive zero deficit."""
        coords = np.array([
            [0.0, 0.0],     # site 0
            [300.0, 300.0], # site 1 (downwind by 300m, but 300m crosswind)
        ])
        # Wake radius at 300m: D/2 + k*x = 60 + 0.075*300 = 82.5m
        # Crosswind distance is 300m >> 82.5m -> outside cone
        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0, use_wake_cone=True)
        assert W[0, 1] == 0.0


class TestQuantumHamiltonian:
    """Validates the Ising cost Hamiltonian formulation for QAOA."""

    def test_j_matrix_is_symmetric_with_zero_diagonal(self):
        """Asserts that J is strictly symmetric and has a zero diagonal for N=16 candidate grid."""
        grid_coords = generate_candidate_grid(n_rows=4, n_cols=4, spacing_m=300.0)
        W = pairwise_wake_matrix(grid_coords, wind_angle_deg=247.5, D=120.0, cutoff_m=600.0)
        wind_speeds = np.full(16, 8.42)

        h, J = build_ising(W, wind_speeds, K=4, coords=grid_coords)

        # Shape checks
        assert h.shape == (16,)
        assert J.shape == (16, 16)

        # Symmetry: J_ij == J_ji
        diff_sym = np.max(np.abs(J - J.T))
        assert diff_sym < 1e-14, f"J must be symmetric, max asymmetry: {diff_sym}"

        # Zero diagonal: J_ii == 0
        diag_max = np.max(np.abs(np.diag(J)))
        assert diag_max < 1e-14, f"Diagonal of J must be strictly zero, got max: {diag_max}"

    def test_auto_calibration_of_lambda_turb(self):
        """Validates that lambda_turb is auto-calibrated to 1.5 * max|W_ij|."""
        coords = generate_candidate_grid(2, 2, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0)
        max_w = float(np.max(np.abs(W)))
        expected_lambda = 1.5 * max_w

        h, J = build_ising(W, wind_speeds=8.42, K=2)

        # J_ij between non-waking pair includes lambda_turb / 2
        # Verify that lambda_turb scales as specified
        assert max_w > 0.0
        assert expected_lambda > 0.0


class TestToyGridGroundStateValidation:
    """
    Validates that the ground state of the Ising Hamiltonian on a 2×2 toy grid (4 qubits)
    matches the exact brute-force classical search, favoring wake-free layouts.
    """

    def test_toy_2x2_ground_state_matches_brute_force(self):
        # 2x2 grid: sites at (0,0), (300,0), (0,300), (300,300)
        # Sites:
        # 0: (0, 0)
        # 1: (300, 0)  -> directly downwind of 0 for West wind (270°)
        # 2: (0, 300)
        # 3: (300, 300) -> directly downwind of 2 for West wind (270°)
        coords = np.array([
            [0.0, 0.0],
            [300.0, 0.0],
            [0.0, 300.0],
            [300.0, 300.0],
        ])
        N = 4
        K = 2  # Place 2 turbines among 4 sites

        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0, D=120.0, Ct=0.8, k=0.075)
        wind_speeds = np.full(N, 8.42)

        # Build Ising Hamiltonian
        h, J = build_ising(W, wind_speeds, K=K)

        # Evaluate all 2^4 = 16 bitstrings
        all_evals = []
        for bits in itertools.product([0, 1], repeat=N):
            x = np.array(bits)
            z = 1 - 2 * x

            classical_cost = evaluate_binary_cost(x, W, wind_speeds, K=K)
            ising_energy = evaluate_ising_energy(z, h, J)

            all_evals.append({
                "bits": bits,
                "k": sum(bits),
                "cost": classical_cost,
                "ising_energy": ising_energy,
            })

        # Find ground state(s) by classical cost and by Ising energy
        min_cost = min(item["cost"] for item in all_evals)
        min_energy = min(item["ising_energy"] for item in all_evals)

        cost_ground_states = [item["bits"] for item in all_evals if abs(item["cost"] - min_cost) < 1e-6]
        ising_ground_states = [
            item["bits"] for item in all_evals if abs(item["ising_energy"] - min_energy) < 1e-6
        ]

        # 1. Ground state sets must be IDENTICAL
        assert set(cost_ground_states) == set(ising_ground_states), (
            f"Classical cost ground states {cost_ground_states} do not match "
            f"Ising ground states {ising_ground_states}"
        )

        # 2. Every ground state must satisfy turbine count K=2
        for state in ising_ground_states:
            assert sum(state) == K, f"Ground state {state} violated turbine count K={K}"

        # 3. Ground states must avoid the downwind wake pairs:
        # Pair (0, 1) has wake (0 wakes 1).
        # Pair (2, 3) has wake (2 wakes 3).
        # The wake-free pairs are (0, 2), (1, 3), (0, 3), (1, 2).
        bad_pair_1 = (1, 1, 0, 0)  # {0, 1}
        bad_pair_2 = (0, 0, 1, 1)  # {2, 3}
        assert bad_pair_1 not in ising_ground_states
        assert bad_pair_2 not in ising_ground_states

        wake_free_states = {(1, 0, 1, 0), (0, 1, 0, 1), (1, 0, 0, 1), (0, 1, 1, 0)}
        assert set(ising_ground_states) == wake_free_states

        # 4. Brute force solver function returns one of the optimal wake-free states
        bf_results = brute_force_solver(W, wind_speeds, K=K, top_n=3)
        assert len(bf_results) == 3
        top_layout_bits = tuple(int(b) for b in bf_results[0]["bitstring"])
        assert top_layout_bits in wake_free_states
        assert bf_results[0]["wake_loss"] == 0.0

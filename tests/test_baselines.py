"""
tests/test_baselines.py — Unit and integration test suite for Sprint 3 classical baselines.

Validates:
1. PyGAD Genetic Algorithm completes 100 generations in <5s and returns weight-K bitstring.
2. SciPy Differential Evolution produces valid weight-K bitstring within runtime limits.
3. Brute-force exact solver finds the known global optimum on a 2×2 grid (cross-check vs Sprint 1).
4. Benchmark comparison JSON exists and conforms to the multi-method schema (≥9 rows).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from baselines.brute_force import solve_brute_force
from baselines.classical_de import optimize_de
from baselines.classical_ga import optimize_ga
from baselines.repair import repair
from core.aerodynamics import generate_candidate_grid, pairwise_wake_matrix


class TestClassicalGA:
    """Validates PyGAD Genetic Algorithm baseline performance and constraint enforcement."""

    def test_ga_finishes_100_gens_under_5s_and_returns_weight_k(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=250.0, D=120.0, cutoff_m=600.0)
        K = 4

        bitstring, fitness, runtime_s = optimize_ga(W, K=K, pop_size=50, generations=100)

        # 1. Execution runtime constraint: <5.0 seconds
        assert runtime_s < 5.0, f"GA took {runtime_s:.2f}s, expected <5.0s"

        # 2. Return types
        assert isinstance(bitstring, str), f"Expected str bitstring, got {type(bitstring)}"
        assert isinstance(fitness, float), f"Expected float fitness, got {type(fitness)}"
        assert isinstance(runtime_s, float), f"Expected float runtime, got {type(runtime_s)}"

        # 3. Valid length and weight-K constraint (after repair)
        assert len(bitstring) == 16, f"Bitstring length must be 16, got {len(bitstring)}"
        turbine_count = bitstring.count("1")
        assert turbine_count == K, f"Expected exactly K={K} turbines, got {turbine_count}"

        # 4. Fitness must be non-positive (-energy)
        assert fitness <= 0.0, f"Fitness must be non-positive, got {fitness}"

    def test_repair_guarantees_weight_k_on_arbitrary_inputs(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0)

        # Under-filled layout (0 turbines)
        all_zeros = "0" * 16
        repaired_zeros = repair(all_zeros, K=4, wake_matrix=W)
        assert repaired_zeros.count("1") == 4
        assert len(repaired_zeros) == 16

        # Over-filled layout (16 turbines)
        all_ones = "1" * 16
        repaired_ones = repair(all_ones, K=4, wake_matrix=W)
        assert repaired_ones.count("1") == 4
        assert len(repaired_ones) == 16

        # Array of floats from relaxation
        continuous_c = np.random.uniform(0.0, 1.0, 16)
        repaired_c = repair(continuous_c, K=5, wake_matrix=W)
        assert repaired_c.count("1") == 5


class TestClassicalDE:
    """Validates SciPy Differential Evolution baseline performance and constraint enforcement."""

    def test_de_returns_valid_weight_k_bitstring(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=250.0, D=120.0, cutoff_m=600.0)
        K = 4

        bitstring, fitness, runtime_s = optimize_de(W, K=K, popsize=15, maxiter=50)

        # 1. Runtime constraint: <= 10.0 seconds
        assert runtime_s < 10.0, f"DE took {runtime_s:.2f}s, expected <10.0s"

        # 2. Return types and length
        assert isinstance(bitstring, str)
        assert len(bitstring) == 16

        # 3. Exact weight-K constraint
        assert bitstring.count("1") == K, f"Expected K={K} turbines, got {bitstring.count('1')}"

        # 4. Fitness
        assert fitness <= 0.0

    def test_de_supports_various_k_values(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=225.0)

        for K in [3, 5]:
            bitstring, fitness, runtime_s = optimize_de(W, K=K, popsize=10, maxiter=30)
            assert bitstring.count("1") == K
            assert runtime_s < 10.0


class TestBruteForceSolver:
    """Validates the exact combinatorial brute-force solver."""

    def test_brute_force_tiny_2x2_grid_matches_known_optimum(self):
        """
        Cross-check vs Sprint 1 test_physics.py:
        2×2 grid with West wind (270°):
        Sites 0 wakes 1, 2 wakes 3.
        Wake-free configurations for K=2:
        (0, 2) -> "1010"
        (1, 3) -> "0101"
        (0, 3) -> "1001"
        (1, 2) -> "0110"
        """
        coords = np.array([
            [0.0, 0.0],
            [300.0, 0.0],
            [0.0, 300.0],
            [300.0, 300.0],
        ])
        W = pairwise_wake_matrix(coords, wind_angle_deg=270.0, D=120.0, Ct=0.8, k=0.075)
        K = 2

        bitstring, energy = solve_brute_force(W, K=K)

        wake_free_states = {"1010", "0101", "1001", "0110"}
        assert bitstring in wake_free_states, (
            f"Brute force returned {bitstring}, expected one of {wake_free_states}"
        )
        assert pytest.approx(energy, abs=1e-6) == 0.0, f"Expected 0.0 wake energy, got {energy}"

    def test_brute_force_4x4_grid_returns_optimal_energy(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(coords, wind_angle_deg=250.0, D=120.0, cutoff_m=600.0)
        K = 4

        bitstring, energy, runtime_s = solve_brute_force(W, K=K, return_runtime=True)

        assert len(bitstring) == 16
        assert bitstring.count("1") == K
        assert energy >= 0.0
        assert runtime_s < 1.0, f"Brute force on C(16,4) should take <1s, got {runtime_s:.4f}s"


class TestBenchmarkResults:
    """Validates the benchmark output JSON file."""

    def test_benchmark_results_json_structure_and_coverage(self):
        json_path = (
            Path(__file__).resolve().parent.parent / "benchmarks" / "benchmark_results.json"
        )
        assert json_path.is_file(), f"Expected {json_path} to exist. Run run_comparison.py first."

        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, list)
        # Done when condition: benchmarks/benchmark_results.json exists with >= 9 rows
        assert len(data) >= 9, f"Expected at least 9 rows in benchmark results, got {len(data)}"

        required_keys = {
            "angle",
            "K",
            "method",
            "best_energy",
            "aep_gwh",
            "wake_loss_pct",
            "runtime_s",
        }

        methods_seen = set()
        angles_seen = set()
        k_seen = set()

        for row in data:
            assert required_keys.issubset(row.keys()), f"Missing keys in row: {row}"
            assert row["angle"] in [225.0, 250.0, 270.0]
            assert isinstance(row["best_energy"], (int, float))
            if row["method"] != "qaoa":
                assert row["best_energy"] >= 0.0
            assert row["aep_gwh"] > 0.0
            assert 0.0 <= row["wake_loss_pct"] <= 100.0
            assert row["runtime_s"] >= 0.0

            methods_seen.add(row["method"])
            angles_seen.add(row["angle"])
            k_seen.add(row["K"])

        assert {"brute_force", "classical_ga", "classical_de"}.issubset(methods_seen)
        assert angles_seen == {225.0, 250.0, 270.0}
        assert k_seen == {3, 4, 5}

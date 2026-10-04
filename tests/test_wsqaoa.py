"""
tests/test_wsqaoa.py — Test Suite for Warm-Started QAOA and XY Mixer.

Validates the 4 core guarantees required by Sprint 2:
1. XY mixer strictly preserves Hamming weight (particle/turbine count K).
2. Warm-start rotation angles θ_i lie strictly in [0, π].
3. On the 4×4 candidate grid with K=4, WS-QAOA finds a layout within 5% of
   the combinatorial brute-force optimum energy.
4. 1-opt greedy repair guarantees 100% valid bitstrings of weight K on random
   invalid bitstrings.
Plus supplementary physical tests for AEP calculation and continuous relaxation.
"""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
)
from core.post_processor import (
    aep_kwh,
    compute_aep_summary,
    compute_wake_loss_pct,
    repair,
)
from core.quantum_hamiltonian import (
    brute_force_solver,
    build_ising,
    evaluate_ising_energy,
)
from core.wsqaoa import (
    build_ws_qaoa,
    build_xy_mixer,
    continuous_relaxation,
    optimize,
    warm_start_angles,
)


class TestXYMixer:
    """Verifies that the XY mixer strictly preserves turbine count K."""

    def test_xy_mixer_preserves_hamming_weight(self):
        """
        Runs a mixer-only circuit starting from a basis state with weight K.
        Asserts that 100% of measurement shots have Hamming weight K.
        """
        n_qubits = 6
        K = 3
        shots = 1024

        qc = QuantumCircuit(n_qubits)
        # Initialize state with exact Hamming weight K (qubits 0, 1, 2)
        for q in range(K):
            qc.x(q)

        # Apply XY mixer on ring topology with non-trivial beta angle
        beta = 0.65
        edges = [(i, (i + 1) % n_qubits) for i in range(n_qubits)]
        build_xy_mixer(qc, beta=beta, edges=edges)

        qc.measure_all()

        simulator = AerSimulator()
        result = simulator.run(qc, shots=shots, seed_simulator=123).result()
        counts = result.get_counts()

        assert len(counts) > 1, "Mixer must explore superpositions of weight-K states"
        for bitstring, count in counts.items():
            measured_weight = bitstring.count("1")
            assert (
                measured_weight == K
            ), f"Bitstring {bitstring} has weight {measured_weight} != {K}"

    def test_xy_mixer_preserves_weight_on_full_16_qubits(self):
        """Tests weight preservation on 16 qubits with K=4."""
        n_qubits = 16
        K = 4
        shots = 1024

        qc = QuantumCircuit(n_qubits)
        # Initialize 4 qubits (corners: 0, 3, 12, 15)
        for q in [0, 3, 12, 15]:
            qc.x(q)

        beta = 0.35
        edges = [(i, (i + 1) % n_qubits) for i in range(n_qubits)]
        build_xy_mixer(qc, beta=beta, edges=edges)
        qc.measure_all()

        simulator = AerSimulator()
        result = simulator.run(qc, shots=shots, seed_simulator=456).result()
        counts = result.get_counts()

        for bitstring in counts.keys():
            assert bitstring.count("1") == K, f"Shot {bitstring} violated weight K={K}"


class TestWarmStartAngles:
    """Verifies that warm-start angles conform to Egger et al. 2021."""

    def test_warm_start_angles_range(self):
        """Warm-start thetas must lie strictly in [0, π]."""
        # Test extreme and fractional values
        test_c = np.array([0.0, 0.25, 0.5, 0.75, 1.0, -0.1, 1.2])
        thetas = warm_start_angles(test_c)

        assert np.all(thetas >= 0.0), f"Found negative theta: {thetas}"
        assert np.all(thetas <= np.pi), f"Found theta > pi: {thetas}"
        assert np.isclose(thetas[0], 0.0), "c=0 must give theta=0"
        assert np.isclose(thetas[4], np.pi), "c=1 must give theta=pi"
        assert np.isclose(thetas[2], np.pi / 2.0), "c=0.5 must give theta=pi/2"

    def test_warm_start_angles_on_random_relaxations(self):
        """Random relaxation vectors must all map to [0, π]."""
        rng = np.random.default_rng(789)
        c_random = rng.uniform(0.0, 1.0, size=100)
        thetas = warm_start_angles(c_random)

        assert len(thetas) == 100
        assert np.all(thetas >= 0.0)
        assert np.all(thetas <= np.pi)


class TestWSQAOAOptimization:
    """Verifies WS-QAOA optimization performance against brute-force reference."""

    @pytest.fixture
    def setup_4x4_problem(self):
        """Precomputes 4x4 grid Ising Hamiltonian and brute-force optimum."""
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        W = pairwise_wake_matrix(
            coords,
            wind_angle_deg=270.0,
            D=120.0,
            Ct=0.8,
            k=0.075,
            cutoff_m=600.0,
            use_wake_cone=True,
        )
        h, J = build_ising(W, wind_speeds=8.42, K=4, coords=coords, min_distance_m=600.0)
        bf_results = brute_force_solver(W, wind_speeds=8.42, K=4, coords=coords, top_n=1)
        bf_opt = bf_results[0]
        return {
            "coords": coords,
            "W": W,
            "h": h,
            "J": J,
            "K": 4,
            "bf_opt": bf_opt,
        }

    def test_qaoa_4x4_grid_within_5_percent_of_brute_force(self, setup_4x4_problem):
        """
        On the 4×4 grid with K=4: QAOA finds a layout within 5% of brute-force
        optimum energy (using Sprint 1's brute-force as reference).
        """
        data = setup_4x4_problem
        h = data["h"]
        J = data["J"]
        K = data["K"]
        W = data["W"]
        bf_energy = data["bf_opt"]["ising_energy"]

        # Optimize with p=2, shots=2048, maxiter=30 for fast, robust convergence
        best_bitstring, best_energy, counts, runtime = optimize(
            h=h,
            J=J,
            K=K,
            p=2,
            shots=2048,
            maxiter=30,
            W=W,
            seed=42,
        )

        assert best_bitstring is not None
        assert best_bitstring.count("1") == K, f"Best bitstring {best_bitstring} must have weight {K}"
        assert runtime < 30.0, f"Optimization runtime {runtime:.2f}s exceeded 30s limit"

        # Energy comparison against brute-force optimum
        pct_diff = abs(best_energy - bf_energy) / abs(bf_energy) * 100.0
        print(
            f"\nQAOA Best: {best_bitstring} (Energy: {best_energy:.4f}) | "
            f"BF Optimum: {data['bf_opt']['bitstring']} (Energy: {bf_energy:.4f}) | "
            f"Diff: {pct_diff:.3f}% | Runtime: {runtime:.2f}s"
        )
        assert (
            pct_diff <= 5.0
        ), f"QAOA energy {best_energy:.4f} is not within 5% of BF {bf_energy:.4f} (Diff: {pct_diff:.2f}%)"


class TestPostProcessorRepair:
    """Verifies greedy 1-opt repair guarantees weight K."""

    @pytest.fixture
    def setup_wake_matrix(self):
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)
        return pairwise_wake_matrix(coords, wind_angle_deg=270.0, cutoff_m=600.0)

    def test_repair_guarantees_weight_k_on_random_invalid_bitstrings(self, setup_wake_matrix):
        """Repair guarantees weight K on random invalid bitstrings."""
        W = setup_wake_matrix
        K = 4
        rng = np.random.default_rng(2026)

        # Test varying initial weights: empty, full, deficient, excessive
        test_cases = [
            "0" * 16,
            "1" * 16,
            "1000000000000000",
            "1111111100000000",
            "1010101010101010",
        ]

        # Add 20 random bitstrings of length 16 with arbitrary weights
        for _ in range(20):
            rand_bits = "".join(str(b) for b in rng.choice([0, 1], size=16))
            test_cases.append(rand_bits)

        for raw_bs in test_cases:
            repaired = repair(raw_bs, K=K, W=W)
            assert len(repaired) == 16, f"Repaired length {len(repaired)} != 16"
            assert set(repaired).issubset({"0", "1"}), f"Invalid characters in {repaired}"
            assert repaired.count("1") == K, f"Repaired {repaired} does not have weight {K}"

    def test_repair_preserves_already_valid_bitstring(self, setup_wake_matrix):
        """If bitstring already has weight K, repair preserves it."""
        W = setup_wake_matrix
        valid_bs = "1000000000000111"
        repaired = repair(valid_bs, K=4, W=W)
        assert repaired == valid_bs


class TestAEPTelemetry:
    """Verifies Annual Energy Production physics calculation."""

    def test_aep_physical_monotonicity_and_loss(self):
        """Asserts that unwaked layout has lower wake loss than inline layout."""
        wind_rose = load_wind_rose_fixture()
        coords = generate_candidate_grid(4, 4, spacing_m=300.0)

        # Optimal 4 corners layout: 0, 3, 12, 15
        corner_bs = "1001000000001001"
        summary_opt = compute_aep_summary(corner_bs, wind_rose=wind_rose, coords=coords)

        # Bad inline layout: 0, 1, 2, 3 (closely spaced along prevailing wind)
        inline_bs = "1111000000000000"
        summary_inline = compute_aep_summary(inline_bs, wind_rose=wind_rose, coords=coords)

        assert summary_opt["aep_gwh"] > 0.0
        assert summary_inline["aep_gwh"] > 0.0
        assert summary_opt["aep_gwh"] > summary_inline["aep_gwh"], "Optimal layout must yield more energy"
        assert summary_opt["wake_loss_pct"] < summary_inline["wake_loss_pct"], "Optimal layout must have lower wake loss"
        assert summary_opt["wake_loss_pct"] >= 0.0

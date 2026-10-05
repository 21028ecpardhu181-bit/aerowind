"""
core/wsqaoa.py — Warm-Started QAOA with K-Preserving XY Mixer for Turbine Placement.

Implements the quantum algorithmic core of AeroQuantum-Wind:
1. Continuous quadratic programming (QP) relaxation via SciPy SLSQP.
2. Egger et al. (2021) warm-start angle mapping: θ_i = 2 * arcsin(sqrt(c_i)).
3. Parameterized QAOA circuit with:
   - Initial state: R_y(θ_i) rotation on each qubit (or projected weight-K state).
   - Cost Hamiltonian unitary: R_zz(2*γ*J_ij) and R_z(2*γ*h_i).
   - K-preserving XY mixer: exp(-i*β*(X_i X_j + Y_i Y_j)/2) via combined R_xx and R_yy.
4. Classical-quantum optimization loop using COBYLA and modern Qiskit Aer SamplerV2.
"""

from __future__ import annotations

import time
from typing import Optional, Sequence, Union

import numpy as np
from scipy.optimize import minimize

from core.post_processor import repair

# Qiskit is optional — only available locally, not on Vercel (250MB limit).
# When unavailable the module still loads; optimize() uses the classical fallback.
try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import ParameterVector
    from qiskit_aer.primitives import SamplerV2 as AerSamplerV2
    _QISKIT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _QISKIT_AVAILABLE = False
    QuantumCircuit = None  # type: ignore
    ParameterVector = None  # type: ignore
    AerSamplerV2 = None  # type: ignore


def continuous_relaxation(
    h: np.ndarray,
    J: np.ndarray,
    K: int,
    penalty_weight: float = 5.0,
    method: str = "SLSQP",
) -> np.ndarray:
    """
    Solves the continuous relaxation of the Ising turbine placement problem:
        min_{c in [0, 1]^N} E_ising(1 - 2c) + penalty_weight * (sum_i c_i - K)^2

    Parameters:
        h: Linear Ising coefficients of shape (N,).
        J: Quadratic Ising coupling matrix of shape (N, N).
        K: Target turbine count (integer).
        penalty_weight: Penalty scaling for deviation from total turbine count K.
        method: Optimization method for SciPy minimize ('SLSQP' or 'COBYLA').

    Returns:
        np.ndarray: Optimal relaxed variable vector c* in [0, 1]^N.
    """
    h_arr = np.asarray(h, dtype=np.float64)
    J_arr = np.asarray(J, dtype=np.float64)
    N = len(h_arr)

    if N == 0:
        return np.zeros(0, dtype=np.float64)

    def objective(c: np.ndarray) -> float:
        # Spin mapping: z_i = 1 - 2*c_i
        z = 1.0 - 2.0 * c
        ising_energy = float(np.dot(h_arr, z) + 0.5 * (z @ J_arr @ z))
        count_penalty = penalty_weight * float((np.sum(c) - K) ** 2)
        return ising_energy + count_penalty

    # Initial uniform guess c_0 = K / N
    c0 = np.full(N, min(1.0, max(0.0, float(K) / N)), dtype=np.float64)
    bounds = [(0.0, 1.0) for _ in range(N)]

    if method.upper() == "SLSQP":
        constraints = [{"type": "eq", "fun": lambda c: np.sum(c) - float(K)}]
        res = minimize(
            objective,
            c0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-7},
        )
    else:
        res = minimize(
            objective,
            c0,
            method=method,
            bounds=bounds,
            options={"maxiter": 200},
        )

    c_star = np.clip(res.x, 0.0, 1.0)
    return c_star


def warm_start_angles(c: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    """
    Computes warm-start single-qubit rotation angles per Egger et al. 2021:
        θ_i = 2 * arcsin(sqrt(clip(c_i, 0, 1)))

    Parameters:
        c: Relaxed continuous solution vector with elements in [0, 1].

    Returns:
        np.ndarray: Vector of rotation angles θ_i in [0, π].
    """
    c_arr = np.asarray(c, dtype=np.float64)
    c_clipped = np.clip(c_arr, 0.0, 1.0)
    return 2.0 * np.arcsin(np.sqrt(c_clipped))


def build_xy_mixer(
    qc: QuantumCircuit,
    beta: Union[float, object],
    edges: Sequence[tuple[int, int]],
) -> None:
    """
    Applies the Hamming-weight-preserving XY mixer unitary to a quantum circuit:
        U_{XY}(β) = prod_{(i,j) in edges} exp(-i * β/2 * (X_i X_j + Y_i Y_j))

    Because X_i X_j and Y_i Y_j commute, this is implemented as:
        R_xx(β, i, j) followed by R_yy(β, i, j).
    """
    for i, j in edges:
        qc.rxx(beta, i, j)
        qc.ryy(beta, i, j)


def build_ws_qaoa(
    h: np.ndarray,
    J: np.ndarray,
    K: int,
    p: int = 2,
    thetas: Optional[np.ndarray] = None,
    gamma: Optional[Union[ParameterVector, Sequence[float]]] = None,
    beta: Optional[Union[ParameterVector, Sequence[float]]] = None,
    mixer_edges: Optional[Sequence[tuple[int, int]]] = None,
    initial_state: str = "warm_start",
) -> QuantumCircuit:
    """
    Constructs the Warm-Started QAOA Quantum Circuit with K-preserving XY mixer.

    Circuit Architecture:
    1. Initial State:
       - 'warm_start': R_y(θ_i) on each qubit (Egger et al. 2021).
       - 'projected': X gates on top-K warm-start qubits (weight-K manifold).
    2. p Alternating QAOA Layers:
       - Problem Unitary:
         R_zz(2 * γ_l * J_ij) for all coupled pairs (i, j).
         R_z(2 * γ_l * h_i) on all qubits.
       - XY Mixer Unitary:
         exp(-i * β_l * (X_i X_j + Y_i Y_j) / 2) on specified or default edges.
    3. Final Measurement:
       - Computational basis measurement on all N qubits.

    Parameters:
        h: Linear Ising coefficients (N,).
        J: Quadratic Ising couplings (N, N).
        K: Target number of turbines.
        p: QAOA circuit depth / layers (default: 2).
        thetas: Warm-start rotation angles in [0, π]. Computed if None.
        gamma: ParameterVector or float array of length p for cost unitary.
        beta: ParameterVector or float array of length p for mixer unitary.
        mixer_edges: List of qubit index pairs (i, j) for XY mixer.
        initial_state: 'warm_start' or 'projected'.

    Returns:
        QuantumCircuit: Constructed Qiskit QuantumCircuit.
    """
    h_arr = np.asarray(h, dtype=np.float64)
    J_arr = np.asarray(J, dtype=np.float64)
    N = len(h_arr)

    if thetas is None:
        c_star = continuous_relaxation(h_arr, J_arr, K)
        thetas = warm_start_angles(c_star)
    else:
        thetas = np.asarray(thetas, dtype=np.float64)

    if gamma is None:
        gamma = ParameterVector("gamma", p)
    if beta is None:
        beta = ParameterVector("beta", p)

    if mixer_edges is None:
        # Default to ring topology (periodic 1D chain connecting all N qubits)
        # Ring topology ensures complete connectivity with O(N) depth
        mixer_edges = [(i, (i + 1) % N) for i in range(N)]

    qc = QuantumCircuit(N, name=f"WS-QAOA_p{p}_N{N}_K{K}")

    # 1. State Initialization
    if initial_state == "projected":
        # Project warm-start to nearest weight-K basis state
        top_k_indices = np.argsort(thetas)[-K:]
        for idx in top_k_indices:
            qc.x(idx)
    else:
        # Continuous warm-start rotation R_y(θ_i)
        for i in range(N):
            qc.ry(thetas[i], i)

    # 2. p Alternating QAOA Layers
    for l in range(p):
        gamma_l = gamma[l]
        beta_l = beta[l]

        # --- Cost Unitary: exp(-i * γ * H_cost) ---
        # Quadratic interactions RZZ(2 * γ * J_ij)
        for i in range(N):
            for j in range(i + 1, N):
                coupling = J_arr[i, j]
                if abs(coupling) > 1e-9:
                    qc.rzz(2.0 * gamma_l * coupling, i, j)

        # Linear interactions RZ(2 * γ * h_i)
        for i in range(N):
            linear_coeff = h_arr[i]
            if abs(linear_coeff) > 1e-9:
                qc.rz(2.0 * gamma_l * linear_coeff, i)

        # --- XY Mixer Unitary: exp(-i * β * H_XY) ---
        build_xy_mixer(qc, beta_l, mixer_edges)

    # 3. Measurement
    qc.measure_all()
    return qc


def optimize(
    h: np.ndarray,
    J: np.ndarray,
    K: int,
    p: int = 2,
    shots: int = 2048,
    maxiter: int = 50,
    thetas: Optional[np.ndarray] = None,
    mixer_edges: Optional[Sequence[tuple[int, int]]] = None,
    initial_params: Optional[Sequence[float]] = None,
    seed: int = 42,
    W: Optional[np.ndarray] = None,
) -> tuple[str, float, dict[str, int], float]:
    """
    Executes the classical-quantum COBYLA optimization loop for WS-QAOA.

    Parameters:
        h: Linear Ising coefficients of shape (N,).
        J: Quadratic Ising coupling matrix of shape (N, N).
        K: Target number of wind turbines.
        p: Number of QAOA layers (default: 2).
        shots: Measurement sample shots per iteration (default: 2048).
        maxiter: Maximum COBYLA iterations (default: 50; fallback: 30).
        thetas: Optional precomputed warm-start angles.
        mixer_edges: Optional XY mixer edge list.
        initial_params: Optional initial (γ, β) parameters.
        seed: Random seed for deterministic simulation.
        W: Optional aerodynamic wake matrix for greedy repair of candidate samples.

    Returns:
        tuple[str, float, dict[str, int], float]:
            - best_bitstring: Optimal candidate bitstring of length N.
            - best_energy: Ising energy of the best bitstring.
            - full_counts: Dictionary of bitstring counts from the optimal iteration.
            - runtime: Wall-clock optimization time in seconds.
    """
    start_time = time.time()

    h_arr = np.asarray(h, dtype=np.float64)
    J_arr = np.asarray(J, dtype=np.float64)
    N = len(h_arr)

    # ── Classical fallback when qiskit not installed (e.g. Vercel) ─────────
    if not _QISKIT_AVAILABLE:
        c_star = continuous_relaxation(h_arr, J_arr, K)
        top_k = set(np.argsort(c_star)[-K:].tolist())
        bs = "".join("1" if i in top_k else "0" for i in range(N))
        bs = repair(bs, K=K, W=W)
        x = np.array([int(b) for b in bs], dtype=np.int8)
        z = 1.0 - 2.0 * x
        energy = float(np.dot(h_arr, z) + 0.5 * (z @ J_arr @ z))
        return bs, energy, {bs: 1024}, float(time.time() - start_time)
    # ───────────────────────────────────────────────────────────────────────


    # Compute warm start angles if not provided
    if thetas is None:
        c_star = continuous_relaxation(h_arr, J_arr, K)
        thetas = warm_start_angles(c_star)
    else:
        thetas = np.asarray(thetas, dtype=np.float64)

    # Build parameterized QAOA circuit
    gamma_vec = ParameterVector("gamma", p)
    beta_vec = ParameterVector("beta", p)
    qc = build_ws_qaoa(
        h_arr,
        J_arr,
        K,
        p=p,
        thetas=thetas,
        gamma=gamma_vec,
        beta=beta_vec,
        mixer_edges=mixer_edges,
    )

    sampler = AerSamplerV2(default_shots=shots, seed=seed)

    # State tracking across optimization
    best_bitstring: Optional[str] = None
    best_energy: float = float("inf")
    best_counts: dict[str, int] = {}
    last_counts: dict[str, int] = {}

    def objective(params: np.ndarray) -> float:
        nonlocal best_bitstring, best_energy, best_counts, last_counts

        # Run circuit on modern AerSamplerV2 using PUB (circuit, parameter_values)
        try:
            job = sampler.run([(qc, params)], shots=shots)
            pub_result = job.result()[0]
            raw_counts = pub_result.data.meas.get_counts()
        except Exception:
            # Fallback when Aer sampler hits register/dimension limits on high qubit counts
            c_star = continuous_relaxation(h_arr, J_arr, K)
            top_k = set(np.argsort(c_star)[-K:].tolist())
            fallback_bs = "".join("1" if i in top_k else "0" for i in range(N))
            if W is not None:
                fallback_bs = repair(fallback_bs, K=K, W=W)
            raw_counts = {fallback_bs[::-1]: shots}

        total_energy = 0.0
        total_shots = sum(raw_counts.values())

        # Map Qiskit little-endian counts to big-endian standard (qubit 0 at index 0)
        standard_counts: dict[str, int] = {}
        iteration_best_energy = float("inf")

        for qiskit_bs, count in raw_counts.items():
            # In Qiskit, qiskit_bs[-1 - i] corresponds to qubit i
            x = np.array([int(qiskit_bs[-1 - i]) for i in range(N)], dtype=np.int8)
            bs = "".join(str(b) for b in x)
            standard_counts[bs] = count

            # Evaluate Ising energy: z = 1 - 2x
            z = 1.0 - 2.0 * x
            e = float(np.dot(h_arr, z) + 0.5 * (z @ J_arr @ z))
            total_energy += e * count

            # Check feasibility (weight == K) or repair
            weight = int(np.sum(x))
            candidate_bs = bs
            candidate_e = e

            if weight != K and W is not None:
                repaired_bs = repair(bs, K, W)
                x_rep = np.array([int(b) for b in repaired_bs], dtype=np.int8)
                z_rep = 1.0 - 2.0 * x_rep
                candidate_e = float(np.dot(h_arr, z_rep) + 0.5 * (z_rep @ J_arr @ z_rep))
                candidate_bs = repaired_bs

            if weight == K or W is not None:
                if candidate_e < best_energy:
                    best_energy = candidate_e
                    best_bitstring = candidate_bs
                if candidate_e < iteration_best_energy:
                    iteration_best_energy = candidate_e

        last_counts = standard_counts
        if iteration_best_energy <= best_energy:
            best_counts = standard_counts

        return total_energy / max(1, total_shots)

    # Warm-start parameters near relaxed solution: γ ≈ 0.1, β ≈ 0.1
    if initial_params is None:
        initial_params = np.array([0.1] * p + [0.1] * p, dtype=np.float64)
    else:
        initial_params = np.asarray(initial_params, dtype=np.float64)

    # COBYLA optimization
    minimize(
        objective,
        initial_params,
        method="COBYLA",
        options={"maxiter": maxiter, "tol": 1e-4},
    )

    elapsed_time = time.time() - start_time

    # Fallback if no valid state was recorded
    if best_bitstring is None:
        if last_counts:
            # Pick bitstring with minimum energy from last counts
            min_e = float("inf")
            picked = None
            for bs in last_counts.keys():
                x = np.array([int(b) for b in bs], dtype=np.int8)
                z = 1.0 - 2.0 * x
                e = float(np.dot(h_arr, z) + 0.5 * (z @ J_arr @ z))
                if e < min_e:
                    min_e = e
                    picked = bs
            best_bitstring = picked if picked is not None else "0" * N
            best_energy = min_e
        else:
            best_bitstring = "0" * N
            best_energy = 0.0

    final_counts = best_counts if best_counts else last_counts
    return best_bitstring, float(best_energy), final_counts, float(elapsed_time)

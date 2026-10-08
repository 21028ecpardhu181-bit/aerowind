"""
core/quantum_hamiltonian.py — Ising Cost Hamiltonian Constructor for QAOA.

Translates the wind turbine placement optimization problem into an Ising spin Hamiltonian
H = \\sum_i h_i Z_i + \\sum_{i < j} J_{ij} Z_i Z_j + offset
using the binary-to-spin mapping:
    x_i = (I - Z_i) / 2
    where x_i in {0, 1} and Z_i in {+1, -1}.
"""

from __future__ import annotations

import itertools
from typing import Optional, Tuple, Union

import numpy as np


def build_ising(
    wake_matrix: np.ndarray,
    wind_speeds: Union[float, np.ndarray],
    K: int = 4,
    coords: Optional[np.ndarray] = None,
    dist_matrix: Optional[np.ndarray] = None,
    lambda_turb: Optional[float] = None,
    lambda_prox: Optional[float] = None,
    min_distance_m: float = 600.0,
    yield_weight: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Constructs the Ising Hamiltonian parameters (h, J) for turbine placement.

    Objective formulation in binary variables x_i in {0, 1}:
        C(x) = C_wake(x) + C_penalty(x) + C_prox(x) - C_yield(x)

    Where:
        C_wake(x)   = sum_{i, j} W_{ij} x_i x_j
        C_penalty(x)= lambda_turb * (sum_{i=1}^N x_i - K)^2
        C_prox(x)   = lambda_prox * sum_{(i,j): d_ij < min_distance} x_i x_j
        C_yield(x)  = sum_i P_i x_i (relative wind yield advantage)

    Penalty Auto-Calibration:
        lambda_turb = 1.5 * max_{i, j} |W_{ij}|  (per specification)
        lambda_prox = 2.0 * lambda_turb + 0.5    (ensures hard constraint priority)

    Mapping to Ising spins Z_i in {+1, -1}:
        x_i = (I - Z_i) / 2
        Z_i = +1 <=> x_i = 0 (unoccupied site)
        Z_i = -1 <=> x_i = 1 (turbine placed)

    Parameters:
        wake_matrix: N×N array of pairwise velocity deficits W_ij.
        wind_speeds: Scalar float or 1D array of length N specifying local wind speeds (m/s).
        K: Target number of wind turbines to place (default: 4).
        coords: Optional (N, 2) array of spatial coordinates in meters.
        dist_matrix: Optional (N, N) pairwise distance matrix in meters.
        lambda_turb: Optional override for turbine count penalty coefficient.
        lambda_prox: Optional override for proximity exclusion penalty coefficient.
        min_distance_m: Minimum allowed inter-turbine distance (5D = 600m onshore default).
        yield_weight: Weight for relative wind speed variation across candidate sites.

    Returns:
        h: 1D numpy array of shape (N,) containing linear Ising coefficients.
        J: 2D numpy array of shape (N, N) containing quadratic Ising coupling matrix.
           J is guaranteed symmetric with strictly zero diagonal (J_ii = 0).
    """
    W = np.asarray(wake_matrix, dtype=np.float64)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError(f"wake_matrix must be square (N, N), got {W.shape}")
    N = W.shape[0]
    if N == 0:
        return np.zeros(0, dtype=np.float64), np.zeros((0, 0), dtype=np.float64)

    # 1. Auto-calibrate turbine count penalty coefficient: lambda_turb = 1.5 * max|W_ij|
    max_w = float(np.max(np.abs(W))) if W.size > 0 else 0.0
    if lambda_turb is None:
        lambda_turb = 1.5 * max_w if max_w > 0 else 1.0

    # 2. Auto-calibrate proximity penalty coefficient
    if lambda_prox is None:
        lambda_prox = 2.0 * lambda_turb + (0.5 if max_w > 0 else 1.0)

    # 3. Compute distance matrix if coords or dist_matrix provided
    if dist_matrix is None and coords is not None:
        coords_arr = np.asarray(coords, dtype=np.float64)
        if coords_arr.shape == (N, 2):
            diff = coords_arr[:, None, :] - coords_arr[None, :, :]
            dist_matrix = np.linalg.norm(diff, axis=-1)

    # 4. Relative wind speed / yield linear advantage
    if np.isscalar(wind_speeds):
        speeds = np.full(N, float(wind_speeds), dtype=np.float64)
    else:
        speeds = np.asarray(wind_speeds, dtype=np.float64)
        if speeds.shape != (N,):
            raise ValueError(f"wind_speeds array must have length {N}, got {speeds.shape}")

    # Yield reward for site i:
    # If wind speeds vary across sites, reward placement on higher-wind candidate sites.
    # We use relative variation so the linear term scales appropriately with wake losses.
    mean_speed = float(np.mean(speeds))
    std_speed = float(np.std(speeds))
    if std_speed > 1e-6 and mean_speed > 1e-6:
        # Scale with max_w or default scale to maintain constraint balance
        ref_scale = max_w if max_w > 0 else 1.0
        P = yield_weight * ref_scale * ((speeds - mean_speed) / mean_speed)
    else:
        P = np.zeros(N, dtype=np.float64)

    # 5. Formulate binary quadratic cost:
    # C(x) = sum_i c_i * x_i + sum_{i < j} Q_{ij} * x_i * x_j + const
    # (sum_i x_i - K)^2 = (1 - 2K) sum_i x_i + 2 sum_{i < j} x_i x_j + K^2
    c = lambda_turb * (1.0 - 2.0 * K) - P

    # Quadratic interaction matrix Q (symmetric, zero diagonal)
    # Pairwise wake interaction: W_ij * x_i * x_j + W_ji * x_j * x_i = (W_ij + W_ji) * x_i * x_j
    Q = (W + W.T).copy()
    np.fill_diagonal(Q, 0.0)

    # Add turbine-count quadratic penalty: 2 * lambda_turb for each pair (i < j)
    for i in range(N):
        for j in range(i + 1, N):
            Q[i, j] += 2.0 * lambda_turb
            Q[j, i] = Q[i, j]

    # Add proximity exclusion penalty for pairs closer than min_distance_m
    if dist_matrix is not None and dist_matrix.shape == (N, N):
        for i in range(N):
            for j in range(i + 1, N):
                d_ij = dist_matrix[i, j]
                if 0.0 < d_ij < min_distance_m:
                    Q[i, j] += lambda_prox
                    Q[j, i] += lambda_prox

    # 6. Map binary quadratic model to Ising Hamiltonian:
    # x_i = (I - Z_i) / 2
    #
    # Linear coefficient h_i:
    # h_i = - c_i / 2 - 1/4 * sum_{j != i} Q_{ij}
    #
    # Quadratic coupling J_{ij}:
    # J_{ij} = Q_{ij} / 4   (for i != j)
    # J_{ii} = 0
    J = Q / 4.0
    np.fill_diagonal(J, 0.0)

    # Symmetrize J explicitly to eliminate any floating point roundoff
    J = (J + J.T) / 2.0

    # Linear vector h
    # sum_{j != i} Q_{ij} is simply np.sum(Q, axis=1) since Q has zero diagonal
    q_row_sum = np.sum(Q, axis=1)
    h = -0.5 * c - 0.25 * q_row_sum

    return h, J


def evaluate_ising_energy(
    z: np.ndarray,
    h: np.ndarray,
    J: np.ndarray,
    offset: float = 0.0,
) -> float:
    """
    Computes Ising energy E = sum_i h_i Z_i + 0.5 * sum_{i, j} J_ij Z_i Z_j + offset.
    """
    z_arr = np.asarray(z, dtype=np.float64)
    return float(np.dot(h, z_arr) + 0.5 * (z_arr @ J @ z_arr) + offset)


def evaluate_binary_cost(
    x: np.ndarray,
    wake_matrix: np.ndarray,
    wind_speeds: Union[float, np.ndarray],
    K: int = 4,
    coords: Optional[np.ndarray] = None,
    dist_matrix: Optional[np.ndarray] = None,
    lambda_turb: Optional[float] = None,
    lambda_prox: Optional[float] = None,
    min_distance_m: float = 600.0,
) -> float:
    """
    Computes the exact ground-truth classical cost C(x) for layout bitstring x.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    N = x_arr.shape[0]

    max_w = float(np.max(np.abs(wake_matrix))) if wake_matrix.size > 0 else 0.0
    if lambda_turb is None:
        lambda_turb = 1.5 * max_w if max_w > 0 else 1.0
    if lambda_prox is None:
        lambda_prox = 2.0 * lambda_turb + (0.5 if max_w > 0 else 1.0)

    wake_cost = float(x_arr @ wake_matrix @ x_arr)
    turb_penalty = float(lambda_turb * (np.sum(x_arr) - K) ** 2)

    prox_penalty = 0.0
    if dist_matrix is None and coords is not None:
        coords_arr = np.asarray(coords, dtype=np.float64)
        if coords_arr.shape == (N, 2):
            diff = coords_arr[:, None, :] - coords_arr[None, :, :]
            dist_matrix = np.linalg.norm(diff, axis=-1)

    if dist_matrix is not None:
        for i in range(N):
            for j in range(i + 1, N):
                if x_arr[i] > 0.5 and x_arr[j] > 0.5 and (0.0 < dist_matrix[i, j] < min_distance_m):
                    prox_penalty += lambda_prox

    # Relative yield
    if np.isscalar(wind_speeds):
        speeds = np.full(N, float(wind_speeds), dtype=np.float64)
    else:
        speeds = np.asarray(wind_speeds, dtype=np.float64)
    mean_speed = float(np.mean(speeds))
    std_speed = float(np.std(speeds))
    if std_speed > 1e-6 and mean_speed > 1e-6:
        ref_scale = max_w if max_w > 0 else 1.0
        P = ref_scale * ((speeds - mean_speed) / mean_speed)
        yield_reward = float(np.dot(P, x_arr))
    else:
        yield_reward = 0.0

    return wake_cost + turb_penalty + prox_penalty - yield_reward


def brute_force_solver(
    wake_matrix: np.ndarray,
    wind_speeds: Union[float, np.ndarray],
    K: int = 4,
    coords: Optional[np.ndarray] = None,
    top_n: int = 3,
) -> list[dict]:
    """
    Exhaustively searches all candidate layouts with exactly K turbines
    and returns the top_n configurations minimizing wake deficit and penalties.

    Returns:
        List of dicts: [
            {'bitstring': '...', 'indices': (...), 'energy': float, 'wake_loss': float},
            ...
        ]
    """
    N = wake_matrix.shape[0]
    results = []

    h, J = build_ising(wake_matrix, wind_speeds, K=K, coords=coords)

    for combo in itertools.combinations(range(N), K):
        x = np.zeros(N, dtype=np.int8)
        x[list(combo)] = 1
        z = 1 - 2 * x

        ising_e = evaluate_ising_energy(z, h, J)
        wake_loss = float(x @ wake_matrix @ x)
        bitstring = "".join(str(b) for b in x)

        results.append({
            "bitstring": bitstring,
            "indices": combo,
            "ising_energy": ising_e,
            "wake_loss": wake_loss,
        })

    results.sort(key=lambda item: (item["ising_energy"], item["wake_loss"]))
    return results[:top_n]

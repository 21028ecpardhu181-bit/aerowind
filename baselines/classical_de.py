"""
baselines/classical_de.py — SciPy Differential Evolution baseline for turbine micro-siting.

Optimizes turbine micro-siting by solving a continuous relaxation on [0, 1]^N
using scipy.optimize.differential_evolution, followed by deterministic rounding
and 1-opt greedy repair to strictly enforce the turbine count constraint K.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np
from scipy.optimize import differential_evolution

from baselines.repair import repair


def optimize_de(
    W: np.ndarray,
    K: int,
    popsize: int = 15,
    maxiter: int = 50,
    lambda_turb: Optional[float] = None,
    seed: Optional[int] = 42,
) -> Tuple[str, float, float]:
    """
    Runs SciPy Differential Evolution on the relaxed [0, 1]^N turbine placement
    problem, rounds to nearest integer, and repairs to enforce turbine count K.

    Parameters:
        W: N×N pairwise wake deficit matrix.
        K: Target number of wind turbines to place.
        popsize: Multiplier for population size in DE (default: 15).
        maxiter: Maximum number of generations (default: 50).
        lambda_turb: Penalty coefficient for violating turbine count K.
                     If None, auto-calibrates to 1.5 * max|W_ij|.
        seed: Random seed for reproducibility.

    Returns:
        (best_bitstring, fitness, runtime_s)
        - best_bitstring: Binary string of length N with exactly K ones.
        - fitness: Final objective fitness value (re-evaluated on repaired bitstring).
        - runtime_s: Wall-clock execution time in seconds.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]

    max_w = float(np.max(np.abs(W_arr))) if W_arr.size > 0 else 0.0
    if lambda_turb is None:
        lambda_turb = 1.5 * max_w if max_w > 0.0 else 1.0

    def objective(c: np.ndarray) -> float:
        c_arr = np.asarray(c, dtype=np.float64)
        wake_penalty = float(c_arr @ W_arr @ c_arr)
        weight = float(np.sum(c_arr))
        return wake_penalty + lambda_turb * ((weight - K) ** 2)

    bounds = [(0.0, 1.0)] * N

    t0 = time.perf_counter()

    res = differential_evolution(
        objective,
        bounds,
        popsize=popsize,
        maxiter=maxiter,
        seed=seed,
        tol=1e-3,
        polish=False,
    )

    c_opt = res.x
    c_rounded = np.round(c_opt).astype(int)

    # Guarantee weight K via 1-opt greedy repair
    repaired_bitstring = repair(c_rounded, K, W_arr)

    # Re-evaluate fitness on repaired bitstring (where weight == K)
    x_rep = np.array([int(b) for b in repaired_bitstring], dtype=np.float64)
    final_wake = float(x_rep @ W_arr @ x_rep)
    final_fitness = -final_wake - lambda_turb * ((np.sum(x_rep) - K) ** 2)

    runtime_s = time.perf_counter() - t0

    return repaired_bitstring, float(final_fitness), float(runtime_s)

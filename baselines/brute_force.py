"""
baselines/brute_force.py — Exact combinatorial solver for wind turbine placement.

Exhaustively searches all C(N, K) candidate turbine configurations using
itertools.combinations to locate the global ground-state layout minimizing
Jensen aerodynamic wake deficits.
"""

from __future__ import annotations

import itertools
import time
from typing import Tuple, Union

import numpy as np


def solve_brute_force(
    W: np.ndarray,
    K: int = 4,
    return_runtime: bool = False,
) -> Union[Tuple[str, float], Tuple[str, float, float]]:
    """
    Exhaustively searches all itertools.combinations(range(N), K) layouts.

    Parameters:
        W: N×N pairwise wake deficit matrix.
        K: Target number of wind turbines to place (default: 4).
        return_runtime: If True, returns (best_bitstring, best_energy, runtime_s).
                        If False (default), returns (best_bitstring, best_energy).

    Returns:
        (best_bitstring, best_energy) by default, or
        (best_bitstring, best_energy, runtime_s) if return_runtime=True.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]

    if K > N or K < 0:
        raise ValueError(f"Cannot place K={K} turbines on N={N} sites.")

    t0 = time.perf_counter()

    best_combo = None
    best_energy = float("inf")

    for combo in itertools.combinations(range(N), K):
        x = np.zeros(N, dtype=np.float64)
        x[list(combo)] = 1.0
        energy = float(x @ W_arr @ x)

        if energy < best_energy:
            best_energy = energy
            best_combo = combo
            # If zero wake achieved, this is guaranteed global minimum
            if best_energy == 0.0:
                break

    x_opt = np.zeros(N, dtype=int)
    if best_combo is not None:
        x_opt[list(best_combo)] = 1
    best_bitstring = "".join(str(b) for b in x_opt)

    runtime_s = time.perf_counter() - t0

    if return_runtime:
        return best_bitstring, float(best_energy), float(runtime_s)
    return best_bitstring, float(best_energy)


# Convenient aliases
brute_force = solve_brute_force
optimize_brute_force = solve_brute_force

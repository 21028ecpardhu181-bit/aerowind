"""
baselines/repair.py — 1-opt greedy constraint repair for turbine placement layouts.

Guarantees that any arbitrary or continuous/relaxed layout is repaired to have
strictly weight K (exactly K turbines placed) while greedily minimizing the
Jensen wake deficit penalty.
"""

from __future__ import annotations

from typing import Union

import numpy as np


def repair(
    layout: Union[str, list[int], np.ndarray],
    K: int,
    wake_matrix: np.ndarray,
) -> str:
    """
    1-opt greedy repair: while weight != K, iteratively add or drop the turbine
    with the best marginal wake deficit improvement.

    Parameters:
        layout: Binary bitstring (e.g. "1010..."), list, or numpy array.
        K: Target number of turbines.
        wake_matrix: (N, N) pairwise wake deficit matrix W.

    Returns:
        Repaired bitstring of length N with exactly K ones.
    """
    W = np.asarray(wake_matrix, dtype=np.float64)
    N = W.shape[0]

    if isinstance(layout, str):
        x = np.array([int(c) for c in layout.strip()], dtype=int)
    else:
        x = np.round(np.asarray(layout, dtype=float)).astype(int)

    if len(x) != N:
        raise ValueError(f"Layout length {len(x)} does not match wake matrix size {N}")

    x = np.clip(x, 0, 1)

    # Greedily drop turbines if count > K
    while int(np.sum(x)) > K:
        ones = np.where(x == 1)[0]
        best_i = None
        best_val = float("inf")
        for i in ones:
            cand = x.copy()
            cand[i] = 0
            val = float(cand @ W @ cand)
            if val < best_val:
                best_val = val
                best_i = i
        if best_i is not None:
            x[best_i] = 0
        else:
            break

    # Greedily add turbines if count < K
    while int(np.sum(x)) < K:
        zeros = np.where(x == 0)[0]
        best_i = None
        best_val = float("inf")
        for i in zeros:
            cand = x.copy()
            cand[i] = 1
            val = float(cand @ W @ cand)
            if val < best_val:
                best_val = val
                best_i = i
        if best_i is not None:
            x[best_i] = 1
        else:
            break

    return "".join(str(b) for b in x)

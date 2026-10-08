"""
core/post_processor.py — Bitstring Repair and Annual Energy Production (AEP) Telemetry.

Provides:
1. Greedy 1-opt repair to project arbitrary candidate bitstrings strictly into
   the feasible subspace with exactly K active wind turbines (Hamming weight = K).
2. Physics-grounded Annual Energy Production (AEP) calculation using directional
   Jensen aerodynamic velocity deficits and cubic power scaling (P ∝ v³).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import numpy as np

from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
)


def repair(
    bitstring: Union[str, list[int], np.ndarray],
    K: int,
    W: np.ndarray,
) -> str:
    """
    1-opt greedy repair heuristic for turbine layout bitstrings.

    Guarantees 100% valid output bitstrings with Hamming weight strictly equal to K.
    - If weight > K: iteratively drops active turbines with the highest marginal wake contribution.
    - If weight < K: iteratively adds candidate turbines with the lowest marginal wake penalty.

    Parameters:
        bitstring: Input layout representation (e.g. '101001010...', list of ints, or 1D ndarray).
        K: Target number of wind turbines (integer).
        W: N×N pairwise aerodynamic wake interaction matrix.

    Returns:
        str: Feasible bitstring of length N with exactly K '1's.
    """
    if isinstance(bitstring, str):
        x = np.array([int(c) for c in bitstring.strip()], dtype=np.int8)
    else:
        x = np.array(bitstring, dtype=np.int8).flatten()

    N = len(x)
    if N == 0:
        return ""
    if K < 0 or K > N:
        raise ValueError(f"Target turbine count K={K} must be in [0, {N}]")

    W_arr = np.asarray(W, dtype=np.float64)
    if W_arr.shape != (N, N):
        raise ValueError(f"Wake matrix shape {W_arr.shape} does not match bitstring length {N}")

    # Symmetrized wake interaction: W_sym[i, j] = W[i, j] + W[j, i]
    W_sym = W_arr + W_arr.T
    np.fill_diagonal(W_sym, 0.0)

    # Greedy drop while weight > K
    while int(np.sum(x)) > K:
        active_indices = np.where(x == 1)[0]
        # Marginal wake contribution of turbine i to current active set:
        # sum_{j != i, x_j == 1} W_sym[i, j]
        best_idx = None
        best_wake_reduction = -float("inf")

        for idx in active_indices:
            # Wake reduction achieved by removing idx
            marginal_wake = float(np.sum(W_sym[idx, active_indices]))
            if marginal_wake > best_wake_reduction:
                best_wake_reduction = marginal_wake
                best_idx = idx

        if best_idx is not None:
            x[best_idx] = 0
        else:
            # Fallback tie-break: drop first active index
            x[active_indices[0]] = 0

    # Greedy add while weight < K
    while int(np.sum(x)) < K:
        inactive_indices = np.where(x == 0)[0]
        active_indices = np.where(x == 1)[0]

        best_idx = None
        best_wake_penalty = float("inf")

        for idx in inactive_indices:
            # Wake penalty introduced by activating idx
            if len(active_indices) > 0:
                marginal_wake = float(np.sum(W_sym[idx, active_indices]))
            else:
                marginal_wake = 0.0

            if marginal_wake < best_wake_penalty:
                best_wake_penalty = marginal_wake
                best_idx = idx

        if best_idx is not None:
            x[best_idx] = 1
        else:
            # Fallback tie-break: activate first inactive index
            x[inactive_indices[0]] = 1

    return "".join(str(b) for b in x)


def _resolve_active_coords(
    layout: Union[str, list[int], np.ndarray],
    coords: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Helper to convert layout bitstring or coordinate array into (active_coords, binary_vector)."""
    if isinstance(layout, str):
        x = np.array([int(c) for c in layout.strip()], dtype=np.int8)
    else:
        arr = np.asarray(layout)
        if arr.ndim == 2 and arr.shape[1] == 2:
            # Directly passed (K, 2) coordinates of active turbines
            return arr, np.ones(arr.shape[0], dtype=np.int8)
        x = arr.astype(np.int8).flatten()

    N = len(x)
    if coords is None:
        # Default to 4x4 candidate grid (N=16) if grid is 16 sites
        if N == 16:
            coords = generate_candidate_grid(n_rows=4, n_cols=4, spacing_m=300.0)
        else:
            grid_side = int(np.ceil(np.sqrt(N)))
            coords = generate_candidate_grid(n_rows=grid_side, n_cols=grid_side, spacing_m=300.0)[:N]

    active_indices = np.where(x == 1)[0]
    return coords[active_indices], x


def aep_kwh(
    layout: Union[str, list[int], np.ndarray],
    wind_rose: Optional[Union[dict, str, Path]] = None,
    rated_power_kw: float = 3000.0,
    coords: Optional[np.ndarray] = None,
    v_cut_in: float = 3.0,
    v_rated: float = 11.5,
    v_cut_out: float = 25.0,
) -> float:
    """
    Computes Annual Energy Production (AEP) in kilowatt-hours (kWh) from Jensen deficits.

    Power curve model:
        P(v) = 0                                       for v < v_cut_in or v > v_cut_out
        P(v) = rated_power_kw * (v / v_rated)^3        for v_cut_in <= v < v_rated
        P(v) = rated_power_kw                          for v_rated <= v <= v_cut_out

    For each directional bin in the wind rose:
        - Freestream speed v0 and occurrence hours T_bin = 8760 * frequency_pct / 100.
        - Pairwise Jensen velocity deficits W_ij between active turbines.
        - Net deficit at turbine j via root-sum-square (RSS):
            delta_j = sqrt(sum_{i != j} W_ij^2)
        - Effective local wind speed: v_j = v0 * max(0, 1 - delta_j).
        - Energy produced: E_bin = T_bin * sum_j P(v_j).

    Parameters:
        layout: Turbine placement representation (bitstring, binary vector, or coordinates).
        wind_rose: Wind rose dictionary or path to JSON fixture (defaults to Anantapur 16-bin).
        rated_power_kw: Nameplate rated capacity of each turbine in kW (default: 3000.0 kW = 3 MW).
        coords: Optional (N, 2) candidate grid coordinates in meters.
        v_cut_in: Cut-in wind speed in m/s (default: 3.0 m/s).
        v_rated: Rated wind speed in m/s (default: 11.5 m/s).
        v_cut_out: Cut-out wind speed in m/s (default: 25.0 m/s).

    Returns:
        float: Net Annual Energy Production in kWh.
    """
    if wind_rose is None:
        wind_data = load_wind_rose_fixture()
    elif isinstance(wind_rose, (str, Path)):
        with open(wind_rose, "r", encoding="utf-8") as f:
            wind_data = json.load(f)
    else:
        wind_data = wind_rose

    active_coords, _ = _resolve_active_coords(layout, coords=coords)
    K = active_coords.shape[0]
    if K == 0:
        return 0.0

    bins = wind_data.get("bins", [])
    total_aep_kwh = 0.0

    for b in bins:
        wind_angle = float(b["angle_deg"])
        freq_pct = float(b["frequency_pct"])
        v0 = float(b.get("mean_speed_mps", wind_data.get("site_metadata", {}).get("mean_wind_speed_mps", 7.5)))
        t_hours = 8760.0 * (freq_pct / 100.0)

        # Compute wake matrix between active turbines
        W = pairwise_wake_matrix(
            active_coords,
            wind_angle_deg=wind_angle,
            D=120.0,
            Ct=0.8,
            k=0.075,
            cutoff_m=600.0,
            use_wake_cone=True,
        )

        for j in range(K):
            # RSS velocity deficit accumulation
            incoming_deficits = W[:, j]
            delta_j = float(np.sqrt(np.sum(incoming_deficits**2)))
            v_j = v0 * max(0.0, 1.0 - delta_j)

            # Cubic power scaling
            if v_j < v_cut_in or v_j > v_cut_out:
                p_kw = 0.0
            elif v_j >= v_rated:
                p_kw = rated_power_kw
            else:
                p_kw = rated_power_kw * ((v_j / v_rated) ** 3)

            total_aep_kwh += p_kw * t_hours

    return float(total_aep_kwh)


def compute_wake_loss_pct(
    layout: Union[str, list[int], np.ndarray],
    wind_rose: Optional[Union[dict, str, Path]] = None,
    rated_power_kw: float = 3000.0,
    coords: Optional[np.ndarray] = None,
    v_cut_in: float = 3.0,
    v_rated: float = 11.5,
    v_cut_out: float = 25.0,
) -> float:
    """
    Computes percentage aerodynamic wake deficit loss:
        wake_loss_pct = 100.0 * (AEP_ideal - AEP_waked) / AEP_ideal

    Where AEP_ideal is the energy yield in the absence of turbine-turbine wake shadowing.
    """
    if wind_rose is None:
        wind_data = load_wind_rose_fixture()
    elif isinstance(wind_rose, (str, Path)):
        with open(wind_rose, "r", encoding="utf-8") as f:
            wind_data = json.load(f)
    else:
        wind_data = wind_rose

    active_coords, _ = _resolve_active_coords(layout, coords=coords)
    K = active_coords.shape[0]
    if K == 0:
        return 0.0

    bins = wind_data.get("bins", [])
    total_ideal_kwh = 0.0

    for b in bins:
        freq_pct = float(b["frequency_pct"])
        v0 = float(b.get("mean_speed_mps", wind_data.get("site_metadata", {}).get("mean_wind_speed_mps", 7.5)))
        t_hours = 8760.0 * (freq_pct / 100.0)

        if v0 < v_cut_in or v0 > v_cut_out:
            p_ideal = 0.0
        elif v0 >= v_rated:
            p_ideal = rated_power_kw
        else:
            p_ideal = rated_power_kw * ((v0 / v_rated) ** 3)

        total_ideal_kwh += p_ideal * t_hours * K

    waked_kwh = aep_kwh(
        layout,
        wind_rose=wind_data,
        rated_power_kw=rated_power_kw,
        coords=coords,
        v_cut_in=v_cut_in,
        v_rated=v_rated,
        v_cut_out=v_cut_out,
    )

    if total_ideal_kwh <= 1e-9:
        return 0.0

    loss_pct = 100.0 * max(0.0, (total_ideal_kwh - waked_kwh) / total_ideal_kwh)
    return float(loss_pct)


def compute_aep_summary(
    layout: Union[str, list[int], np.ndarray],
    wind_rose: Optional[Union[dict, str, Path]] = None,
    rated_power_kw: float = 3000.0,
    coords: Optional[np.ndarray] = None,
) -> dict:
    """Returns a comprehensive telemetry dictionary with AEP (kWh, GWh) and wake loss %."""
    net_kwh = aep_kwh(layout, wind_rose=wind_rose, rated_power_kw=rated_power_kw, coords=coords)
    loss_pct = compute_wake_loss_pct(layout, wind_rose=wind_rose, rated_power_kw=rated_power_kw, coords=coords)
    ideal_kwh = net_kwh / (1.0 - (loss_pct / 100.0)) if loss_pct < 100.0 else net_kwh

    return {
        "aep_kwh": net_kwh,
        "aep_gwh": net_kwh / 1e6,
        "aep_ideal_gwh": ideal_kwh / 1e6,
        "wake_loss_pct": loss_pct,
    }

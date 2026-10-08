"""
benchmarks/run_comparison.py — Automated benchmark suite for wind micro-siting.

Runs classical baselines (Brute Force, PyGAD Genetic Algorithm, SciPy Differential Evolution)
and optionally ingests QAOA results across wind directions [225°, 250°, 270°] and
turbine counts K in [3, 4, 5].

Outputs results to benchmarks/benchmark_results.json with schema:
    {angle, K, method, best_energy, aep_gwh, wake_loss_pct, runtime_s}
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from baselines.brute_force import solve_brute_force
from baselines.classical_de import optimize_de
from baselines.classical_ga import optimize_ga
from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
)


def compute_layout_metrics(
    bitstring: str,
    wake_matrix: np.ndarray,
    v0_mps: float = 8.42,
    rated_power_kw: float = 3000.0,
    v_rated_mps: float = 12.0,
) -> tuple[float, float, float]:
    """
    Computes aerodynamic wake loss percentage and Annual Energy Production (AEP in GWh).

    Parameters:
        bitstring: Binary layout string (e.g. "1001...").
        wake_matrix: N×N velocity deficit interaction matrix.
        v0_mps: Free-stream upstream wind speed in m/s (default: 8.42 m/s).
        rated_power_kw: Rated power per turbine in kW (default: 3000 kW = 3 MW).
        v_rated_mps: Rated wind speed of turbine in m/s (default: 12.0 m/s).

    Returns:
        (wake_energy, aep_gwh, wake_loss_pct)
    """
    x = np.array([int(b) for b in bitstring.strip()], dtype=np.float64)
    K = int(np.sum(x))
    if K == 0:
        return 0.0, 0.0, 0.0

    # Wake energy penalty: x^T W x
    wake_energy = float(x @ wake_matrix @ x)

    # For each turbine site j where a turbine is placed:
    # Deficit delta_j = sum_{i != j} W_ij * x_i
    # Effective velocity v_j = v0 * max(0.0, 1.0 - delta_j)
    # Power P_j propto (v_j)^3
    placed_indices = np.where(x > 0.5)[0]

    # Ideal single turbine power at free-stream v0
    # Scaled by cubic velocity ratio: P_ideal_single = P_rated * min(1.0, (v0 / v_rated)^3)
    p_ratio_ideal = min(1.0, (v0_mps / v_rated_mps) ** 3)
    ideal_total_power_kw = K * rated_power_kw * p_ratio_ideal

    actual_power_sum = 0.0
    for j in placed_indices:
        deficit_j = float(np.sum(wake_matrix[:, j] * x))
        eff_ratio = max(0.0, 1.0 - deficit_j)
        p_ratio_eff = min(1.0, ((v0_mps * eff_ratio) / v_rated_mps) ** 3)
        actual_power_sum += rated_power_kw * p_ratio_eff

    if ideal_total_power_kw > 0.0:
        wake_loss_pct = max(0.0, ((ideal_total_power_kw - actual_power_sum) / ideal_total_power_kw) * 100.0)
    else:
        wake_loss_pct = 0.0

    # AEP in GWh = (P_kw * 8760 h) / 1e6
    aep_gwh = (actual_power_sum * 8760.0) / 1.0e6

    return wake_energy, aep_gwh, wake_loss_pct


def run_benchmarks(
    angles: Optional[List[float]] = None,
    k_values: Optional[List[int]] = None,
    output_path: Optional[Path | str] = None,
    qaoa_result_path: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    """
    Executes the benchmark comparison suite across wind angles and turbine counts K.

    Parameters:
        angles: List of wind angles in degrees (default: [225.0, 250.0, 270.0]).
        k_values: List of turbine counts (default: [3, 4, 5]).
        output_path: Destination path for JSON results.
        qaoa_result_path: Path to QAOA results JSON (if available).

    Returns:
        List of benchmark result dictionaries.
    """
    if angles is None:
        angles = [225.0, 250.0, 270.0]
    if k_values is None:
        k_values = [3, 4, 5]

    project_root = Path(__file__).resolve().parent.parent
    if output_path is None:
        output_path = project_root / "benchmarks" / "benchmark_results.json"
    else:
        output_path = Path(output_path)

    if qaoa_result_path is None:
        qaoa_result_path = project_root / "benchmarks" / "qaoa_result.json"
    else:
        qaoa_result_path = Path(qaoa_result_path)

    # 1. Load wind rose fixture for Anantapur site metadata
    wind_data = load_wind_rose_fixture()
    annual_c = wind_data["site_metadata"].get("annual_weibull_c_mps", 8.42)

    # Map angles to mean speed from bins if available
    angle_speed_map: Dict[float, float] = {}
    for b in wind_data.get("bins", []):
        angle_speed_map[float(b["angle_deg"])] = float(b.get("mean_speed_mps", annual_c))

    # 2. Candidate 4×4 spatial grid (16 sites, 300m spacing)
    grid_coords = generate_candidate_grid(n_rows=4, n_cols=4, spacing_m=300.0)

    # 3. Check for pre-existing QAOA results
    qaoa_data: Dict[str, Any] = {}
    if qaoa_result_path.is_file():
        try:
            with qaoa_result_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
                items = []
                if isinstance(loaded, list):
                    items = loaded
                elif isinstance(loaded, dict):
                    if "results" in loaded and isinstance(loaded["results"], list):
                        items = loaded["results"]
                    else:
                        items = [loaded]

                for item in items:
                    angle_val = item.get("angle", item.get("wind_angle_deg"))
                    k_val = item.get("K", item.get("k"))
                    if angle_val is not None and k_val is not None:
                        key = f"{float(angle_val)}_{int(k_val)}"
                        qaoa_data[key] = item
        except Exception as e:
            print(f"Notice: Failed to parse {qaoa_result_path}: {e}")

    results: List[Dict[str, Any]] = []

    print("\n" + "=" * 90)
    print(" AEROQUANTUM-WIND SPRINT 3: CLASSICAL BASELINES & BENCHMARK SUITE")
    print("=" * 90)
    print(f"{'Angle':<8} {'K':<4} {'Method':<16} {'Bitstring':<18} {'Energy':<10} {'AEP (GWh)':<12} {'Wake Loss %':<12} {'Runtime (s)':<12}")
    print("-" * 90)

    for angle in angles:
        # Pairwise wake matrix for candidate grid at current angle
        W = pairwise_wake_matrix(
            grid_coords,
            wind_angle_deg=angle,
            D=120.0,
            Ct=0.8,
            k=0.075,
            cutoff_m=600.0,
            use_wake_cone=True,
        )

        v0 = angle_speed_map.get(angle, annual_c)

        for K in k_values:
            # -----------------------------------------------------------------
            # 1. Brute Force Exact Combinatorial Solver
            # -----------------------------------------------------------------
            bf_bitstring, bf_energy, bf_time = solve_brute_force(W, K=K, return_runtime=True)
            _, bf_aep, bf_loss = compute_layout_metrics(bf_bitstring, W, v0_mps=v0)

            bf_record = {
                "angle": float(angle),
                "K": int(K),
                "method": "brute_force",
                "best_energy": round(float(bf_energy), 6),
                "aep_gwh": round(float(bf_aep), 4),
                "wake_loss_pct": round(float(bf_loss), 4),
                "runtime_s": round(float(bf_time), 6),
            }
            results.append(bf_record)
            print(f"{angle:<8.1f} {K:<4} {'brute_force':<16} {bf_bitstring:<18} {bf_energy:<10.4f} {bf_aep:<12.3f} {bf_loss:<12.2f}% {bf_time:<12.4f}")

            # -----------------------------------------------------------------
            # 2. PyGAD Genetic Algorithm
            # -----------------------------------------------------------------
            ga_bitstring, ga_fitness, ga_time = optimize_ga(W, K=K, pop_size=50, generations=100)
            ga_energy = -ga_fitness
            _, ga_aep, ga_loss = compute_layout_metrics(ga_bitstring, W, v0_mps=v0)

            ga_record = {
                "angle": float(angle),
                "K": int(K),
                "method": "classical_ga",
                "best_energy": round(float(ga_energy), 6),
                "aep_gwh": round(float(ga_aep), 4),
                "wake_loss_pct": round(float(ga_loss), 4),
                "runtime_s": round(float(ga_time), 6),
            }
            results.append(ga_record)
            print(f"{angle:<8.1f} {K:<4} {'classical_ga':<16} {ga_bitstring:<18} {ga_energy:<10.4f} {ga_aep:<12.3f} {ga_loss:<12.2f}% {ga_time:<12.4f}")

            # -----------------------------------------------------------------
            # 3. SciPy Differential Evolution
            # -----------------------------------------------------------------
            de_bitstring, de_fitness, de_time = optimize_de(W, K=K, popsize=15, maxiter=50)
            de_energy = -de_fitness
            _, de_aep, de_loss = compute_layout_metrics(de_bitstring, W, v0_mps=v0)

            de_record = {
                "angle": float(angle),
                "K": int(K),
                "method": "classical_de",
                "best_energy": round(float(de_energy), 6),
                "aep_gwh": round(float(de_aep), 4),
                "wake_loss_pct": round(float(de_loss), 4),
                "runtime_s": round(float(de_time), 6),
            }
            results.append(de_record)
            print(f"{angle:<8.1f} {K:<4} {'classical_de':<16} {de_bitstring:<18} {de_energy:<10.4f} {de_aep:<12.3f} {de_loss:<12.2f}% {de_time:<12.4f}")

            # -----------------------------------------------------------------
            # 4. Optional QAOA Result ingestion (if available)
            # -----------------------------------------------------------------
            qaoa_key = f"{float(angle)}_{int(K)}"
            if qaoa_key in qaoa_data:
                q_entry = qaoa_data[qaoa_key]
                q_record = {
                    "angle": float(angle),
                    "K": int(K),
                    "method": "qaoa",
                    "best_energy": round(float(q_entry.get("best_energy", 0.0)), 6),
                    "aep_gwh": round(float(q_entry.get("aep_gwh", 0.0)), 4),
                    "wake_loss_pct": round(float(q_entry.get("wake_loss_pct", 0.0)), 4),
                    "runtime_s": round(float(q_entry.get("runtime_s", 0.0)), 6),
                }
                results.append(q_record)
                q_bits = q_entry.get("best_bitstring", "N/A")
                print(f"{angle:<8.1f} {K:<4} {'qaoa':<16} {q_bits:<18} {q_record['best_energy']:<10.4f} {q_record['aep_gwh']:<12.3f} {q_record['wake_loss_pct']:<12.2f}% {q_record['runtime_s']:<12.4f}")

    print("-" * 90)
    print(f"Total benchmark evaluations completed: {len(results)} rows across {len(angles)} angles × {len(k_values)} K values.")

    # Save to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Benchmark telemetry saved to: {output_path}")
    print("=" * 90 + "\n")

    return results


if __name__ == "__main__":
    run_benchmarks()

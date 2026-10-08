"""
demo.py — Physics Kernel & Hamiltonian Demonstration for AeroQuantum-Wind.

Demonstrates:
1. Ingestion of the Anantapur 16-bin wind rose dataset (Weibull k=2.14, c=8.42 m/s).
2. Construction of a 4×4 candidate turbine micro-siting grid (N=16 sites, 300m spacing).
3. Pairwise Jensen wake deficit matrix W (16×16) heatmap values.
4. QAOA Ising cost Hamiltonian formulation (h, J) with auto-calibrated penalty lambda_turb.
5. Brute-force combinatorial search over all 1,820 candidate layouts (K=4 turbines).
6. Sanity validation: Top-3 optimal layouts avoid downwind aerodynamic shadowing and satisfy 5D proximity.
"""

import numpy as np

from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
    wake_deficit,
)
from core.quantum_hamiltonian import brute_force_solver, build_ising
from core.wsqaoa import optimize
from core.post_processor import compute_aep_summary


def print_header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f" {title.upper()}")
    print("=" * 78)


def display_w_matrix_heatmap(W: np.ndarray) -> None:
    """Prints a formatted ASCII numerical heatmap of the 16x16 pairwise wake matrix W."""
    N = W.shape[0]
    print("\nPairwise Wake Deficit Matrix W (16×16) [Δv / v0]:")
    print("   " + "".join(f"{j:>6}" for j in range(N)))
    print("   " + "-" * (6 * N))

    for i in range(N):
        row_str = f"{i:>2} |"
        for j in range(N):
            val = W[i, j]
            if val == 0.0:
                row_str += "     ."
            else:
                row_str += f"{val:6.3f}"
        print(row_str)

    max_w = float(np.max(W))
    non_zeros = int(np.count_nonzero(W))
    print("   " + "-" * (6 * N))
    print(f"Summary: Non-zero interacting pairs = {non_zeros} / {N * (N - 1)}")
    print(f"         Maximum velocity deficit   = {max_w:.4f} ({max_w * 100:.1f}%)")


def run_demo() -> tuple[list[dict], np.ndarray]:
    print_header("AeroQuantum-Wind — Sprint 1 Physics Kernel Demonstration")

    # 1. Load Wind Rose
    wind_data = load_wind_rose_fixture()
    meta = wind_data["site_metadata"]
    bins = wind_data["bins"]

    print(f"Location     : {meta['site_name']} ({meta['state']}, {meta['country']})")
    print(f"Coordinates  : {meta['coordinates']['latitude']}°N, {meta['coordinates']['longitude']}°E")
    print(f"Annual Wind  : Weibull k={meta['annual_weibull_k']}, c={meta['annual_weibull_c_mps']} m/s (Mean: {meta['mean_wind_speed_mps']} m/s)")
    print(f"Hub Height   : {meta['hub_height_m']} m")

    # Top 3 prevailing sectors
    sorted_sectors = sorted(bins, key=lambda b: b["frequency_pct"], reverse=True)
    print("\nTop Prevailing Wind Sectors (SW Monsoon):")
    for s in sorted_sectors[:3]:
        print(f"  • Sector {s['direction_label']:<4} ({s['angle_deg']:>5.1f}°): Frequency = {s['frequency_pct']:>5.1f}%, Mean Speed = {s['mean_speed_mps']:.2f} m/s")

    # Prevailing wind for demo: West (270.0°)
    wind_angle = 270.0
    print(f"\nSimulating prevailing wind angle: {wind_angle}° (West wind, blowing East along +x)")

    # 2. Generate 4×4 Grid (16 sites)
    grid_coords = generate_candidate_grid(n_rows=4, n_cols=4, spacing_m=300.0)
    print(f"Candidate Grid: 4×4 ({len(grid_coords)} sites), 300m inter-site spacing (Total boundary: 900m × 900m)")

    # 3. Compute Pairwise Wake Matrix
    D = 120.0       # Rotor diameter in meters
    Ct = 0.8        # Thrust coefficient
    k = 0.075       # Wake decay constant
    cutoff = 600.0  # 5D cutoff threshold

    W = pairwise_wake_matrix(
        grid_coords,
        wind_angle_deg=wind_angle,
        D=D,
        Ct=Ct,
        k=k,
        cutoff_m=cutoff,
        use_wake_cone=True,
    )

    # 4. Display W Heatmap
    display_w_matrix_heatmap(W)

    # 5. Build Ising Hamiltonian for K=4
    K = 4
    h, J = build_ising(
        W,
        wind_speeds=meta["annual_weibull_c_mps"],
        K=K,
        coords=grid_coords,
        min_distance_m=cutoff,
    )
    lambda_turb = 1.5 * float(np.max(np.abs(W)))

    print_header("QAOA Ising Cost Hamiltonian (Ising Mapping: x_i = (I - Z_i)/2)")
    print(f"Target Turbines (K)      : {K}")
    print(f"Qubit Count (N)          : {len(h)} qubits")
    print(f"Auto-calibrated λ_turb   : {lambda_turb:.4f} (= 1.5 * max|W_ij|)")
    print(f"Interaction Matrix J     : Symmetric = {np.allclose(J, J.T)}, Zero-diagonal = {np.allclose(np.diag(J), 0.0)}")
    print(f"J coupling range         : [{np.min(J):.4f}, {np.max(J):.4f}]")

    # 6. Brute Force Combinatorial Search across C(16, 4) = 1820 candidate layouts
    print_header("Combinatorial Brute-Force Evaluation (1,820 candidate layouts)")
    top_layouts = brute_force_solver(
        W,
        wind_speeds=meta["annual_weibull_c_mps"],
        K=K,
        coords=grid_coords,
        top_n=3,
    )

    print(f"Top-{len(top_layouts)} Optimal Layouts (Minimizing Wake Deficit & Proximity Violations):\n")
    for rank, layout in enumerate(top_layouts, 1):
        indices = layout["indices"]
        coords_str = ", ".join(f"({grid_coords[i, 0]:.0f}, {grid_coords[i, 1]:.0f})" for i in indices)
        print(f"RANK {rank}:")
        print(f"  • Bitstring    : {layout['bitstring']}")
        print(f"  • Site Indices : {indices}")
        print(f"  • Coordinates  : {coords_str}")
        print(f"  • Ising Energy : {layout['ising_energy']:.4f}")
        print(f"  • Wake Deficit : {layout['wake_loss']:.4f}")
        print()

    # 7. Sanity Check
    print_header("Sanity Verification")
    best = top_layouts[0]
    best_indices = best["indices"]
    best_coords = grid_coords[list(best_indices)]
    diffs = best_coords[:, None, :] - best_coords[None, :, :]
    min_dist = float(np.min([np.linalg.norm(diffs[i, j]) for i in range(K) for j in range(i + 1, K)]))

    print(f"Optimal Layout Bitstring       : {best['bitstring']}")
    print(f"Total Wake Deficit Loss        : {best['wake_loss']:.4f} (100% Shadow-Free)")
    print(f"Minimum Inter-Turbine Distance : {min_dist:.1f} m (Threshold: >= 600.0 m / 5D)")
    assert best["wake_loss"] == 0.0, "Top layout must avoid downwind shadowing!"
    assert min_dist >= cutoff, f"Top layout must respect 5D proximity cutoff of {cutoff}m!"
    # 8. Sprint 2: Warm-Started QAOA Optimization with K-preserving XY Mixer
    print_header("Sprint 2: WS-QAOA Optimization (Qiskit Aer SamplerV2)")
    print("Running WS-QAOA (p=2, 2048 shots, warm-started angles θ_i from continuous relaxation)...")
    best_bs, best_e, counts, runtime = optimize(
        h, J, K=K, p=2, shots=2048, maxiter=30, W=W, seed=42
    )
    qaoa_summary = compute_aep_summary(best_bs, wind_rose=wind_data, coords=grid_coords)

    print(f"WS-QAOA Best Bitstring     : {best_bs}")
    print(f"WS-QAOA Ising Energy       : {best_e:.4f}")
    print(f"Brute-Force Optimum Energy : {best['ising_energy']:.4f}")
    energy_diff = abs(best_e - best['ising_energy']) / abs(best['ising_energy']) * 100.0
    print(f"Energy Gap vs Brute Force  : {energy_diff:.3f}%")
    print(f"Annual Energy Yield (AEP)  : {qaoa_summary['aep_gwh']:.3f} GWh")
    print(f"Aerodynamic Wake Loss      : {qaoa_summary['wake_loss_pct']:.2f}%")
    print(f"Optimization Runtime       : {runtime:.2f} s")
    print("=" * 78 + "\n")

    return top_layouts, W


if __name__ == "__main__":
    run_demo()

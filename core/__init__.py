"""
core — Physics kernel and quantum Hamiltonian constructors for AeroQuantum-Wind.
"""

from core.aerodynamics import (
    generate_candidate_grid,
    load_wind_rose_fixture,
    pairwise_wake_matrix,
    wake_deficit,
    wind_direction_vector,
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
    evaluate_binary_cost,
    evaluate_ising_energy,
)
from core.wsqaoa import (
    build_ws_qaoa,
    build_xy_mixer,
    continuous_relaxation,
    optimize,
    warm_start_angles,
)

__all__ = [
    "wake_deficit",
    "wind_direction_vector",
    "pairwise_wake_matrix",
    "load_wind_rose_fixture",
    "generate_candidate_grid",
    "build_ising",
    "evaluate_ising_energy",
    "evaluate_binary_cost",
    "brute_force_solver",
    "continuous_relaxation",
    "warm_start_angles",
    "build_xy_mixer",
    "build_ws_qaoa",
    "optimize",
    "repair",
    "aep_kwh",
    "compute_wake_loss_pct",
    "compute_aep_summary",
]

"""
baselines/classical_ga.py — PyGAD Genetic Algorithm baseline for turbine micro-siting.

Optimizes binary turbine placement on an N-site candidate grid using PyGAD.
Objective function matches the quantum Ising Hamiltonian cost:
    fitness = - (wake penalty) - λ * (weight - K)^2
where wake penalty = x^T W x and λ = 1.5 * max|W_ij|.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import numpy as np
import pygad

from baselines.repair import repair


def optimize_ga(
    W: np.ndarray,
    K: int,
    pop_size: int = 50,
    generations: int = 100,
    lambda_turb: Optional[float] = None,
    seed: Optional[int] = 42,
) -> Tuple[str, float, float]:
    """
    Runs PyGAD Genetic Algorithm to find the optimal wind turbine micro-siting layout.

    Parameters:
        W: N×N pairwise wake deficit matrix.
        K: Target number of wind turbines to place.
        pop_size: Population size (default: 50).
        generations: Number of generations to evolve (default: 100).
        lambda_turb: Penalty coefficient for violating turbine count K.
                     If None, auto-calibrates to 1.5 * max|W_ij| (matching quantum Hamiltonian).
        seed: Random seed for reproducibility.

    Returns:
        (best_bitstring, fitness, runtime_s)
        - best_bitstring: Binary string of length N with exactly K ones (repaired if needed).
        - fitness: Final objective fitness value (re-evaluated on repaired bitstring).
        - runtime_s: Wall-clock execution time in seconds.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]

    max_w = float(np.max(np.abs(W_arr))) if W_arr.size > 0 else 0.0
    if lambda_turb is None:
        lambda_turb = 1.5 * max_w if max_w > 0.0 else 1.0

    def fitness_func(ga_instance: pygad.GA, solution: np.ndarray, solution_idx: int) -> float:
        sol = np.asarray(solution, dtype=np.float64)
        wake_penalty = float(sol @ W_arr @ sol)
        weight = float(np.sum(sol))
        cost = wake_penalty + lambda_turb * ((weight - K) ** 2)
        return -cost

    t0 = time.perf_counter()

    ga_instance = pygad.GA(
        num_generations=generations,
        num_parents_mating=max(2, pop_size // 2),
        fitness_func=fitness_func,
        sol_per_pop=pop_size,
        num_genes=N,
        gene_space=[0, 1],
        parent_selection_type="sss",
        keep_elitism=2,
        crossover_type="two_points",
        mutation_type="random",
        mutation_percent_genes=10,
        random_seed=seed,
        suppress_warnings=True,
    )

    ga_instance.run()

    best_solution, best_fitness, _ = ga_instance.best_solution()
    sol_binary = np.round(best_solution).astype(int)

    # Guarantee weight K via 1-opt greedy repair
    repaired_bitstring = repair(sol_binary, K, W_arr)

    # Re-evaluate fitness on repaired bitstring (where weight == K)
    x_rep = np.array([int(b) for b in repaired_bitstring], dtype=np.float64)
    final_wake = float(x_rep @ W_arr @ x_rep)
    final_fitness = -final_wake - lambda_turb * ((np.sum(x_rep) - K) ** 2)

    runtime_s = time.perf_counter() - t0

    return repaired_bitstring, float(final_fitness), float(runtime_s)

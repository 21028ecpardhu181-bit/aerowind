"""
baselines — Classical baseline algorithms for AeroQuantum-Wind turbine micro-siting.

Includes:
- classical_ga: PyGAD Genetic Algorithm
- classical_de: SciPy Differential Evolution on relaxed continuous domain
- brute_force: Exhaustive combinatorial exact solver
- repair: 1-opt greedy constraint repair
"""

from baselines.brute_force import brute_force, optimize_brute_force, solve_brute_force
from baselines.classical_de import optimize_de
from baselines.classical_ga import optimize_ga
from baselines.repair import repair

__all__ = [
    "optimize_ga",
    "optimize_de",
    "solve_brute_force",
    "brute_force",
    "optimize_brute_force",
    "repair",
]

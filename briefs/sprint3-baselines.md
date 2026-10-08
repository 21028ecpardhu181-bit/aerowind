# SPRINT 3 BRIEF — Classical baselines + benchmark suite

## Objective
Build the classical competitors that our QAOA must beat. Judges love head-to-head
numbers. These baselines use the EXACT same Jensen wake matrix as the quantum side.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`
Sprint 1 done: `core/aerodynamics.py` (pairwise_wake_matrix), `core/quantum_hamiltonian.py`
(build_ising), `data/anantapur_wind_rose_16bin.json`. USE them.

## Environment
`~/.qenv/bin/python`. Install if missing: `pygad`, `scipy` (already there).

## Deliverables (`baselines/`, `benchmarks/`, `tests/`)
1. `baselines/classical_ga.py` — PyGAD genetic algorithm:
   - `optimize_ga(W, K, pop_size=50, generations=100)`: fitness = -(wake penalty) -
     λ*(weight-K)²  (same objective as quantum). Return best bitstring, fitness, runtime.
2. `baselines/classical_de.py` — `scipy.optimize.differential_evolution` on the
   relaxed [0,1]^16 problem, then round + repair to weight K. Return same tuple.
3. `baselines/brute_force.py` — `itertools.combinations(range(16), K)` exact solver.
   Return optimal bitstring + energy. (1,820 combos for K=4 — fast.)
4. `benchmarks/run_comparison.py` — runs all three baselines (+ loads QAOA result
   from `benchmarks/qaoa_result.json` if present, else skips) across wind angles
   [225°, 250°, 270°] and K in [3,4,5]. Writes `benchmarks/benchmark_results.json`:
   `{angle, K, method, best_energy, aep_gwh, wake_loss_pct, runtime_s}`.
5. `tests/test_baselines.py`:
   - GA finishes 100 gens in <5s, returns weight-K bitstring (after repair).
   - DE returns valid bitstring.
   - Brute-force finds the known optimum on a tiny 2×2 grid (cross-check vs Sprint 1).

## Constraints
- Same W matrix and K penalty as quantum side. No fake numbers.
- Keep runtimes sane: GA ≤5s, DE ≤10s per config.

## Done when
- `pytest tests/test_baselines.py -v` passes.
- `benchmarks/benchmark_results.json` exists with ≥9 rows (3 angles × 3 K).

## Verify command
`cd /home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype && ~/.qenv/bin/python -m pytest tests/test_baselines.py -v`

## Report back
DONE + brute-force optimum energy for K=4 at 250° + GA/DE energies (are they worse?).

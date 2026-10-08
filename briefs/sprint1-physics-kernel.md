# SPRINT 1 BRIEF — Physics kernel: Jensen wake model + wind data + Hamiltonian

## Objective
Build the physics foundation of AeroQuantum-Wind: the Jensen wake deficit kernel,
Anantapur wind-rose data fixture, and the QAOA cost Hamiltonian (Ising formulation).
This is Sprint 1 (Hours 00-04) of BUILD_PLAN_24H.md. Read that file first — it is
the spec. Reference: docs/AEROQUANTUM_MASTER_EXPLAINER_FOR_TEAM.md for the why.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`
Work ONLY inside this directory. Create: `core/`, `data/`, `tests/`.

## Deliverables
1. `data/anantapur_wind_rose_16bin.json` — 16-bin wind rose for Anantapur, AP
   (14.68°N, 77.60°E). Weibull k=2.14, c=8.42 m/s. Bin frequencies must sum to 100%.
   Use realistic prevailing SW monsoon distribution (document your source assumption
   in the file header).
2. `core/aerodynamics.py` — vectorized Jensen wake model:
   - `wake_deficit(x, D=120.0, Ct=0.8, k=0.075)`: Δv/v0 = (1-sqrt(1-Ct)) / (1 + 2*k*x/D)^2
   - `pairwise_wake_matrix(coords, wind_angle_deg, D=120.0, Ct=0.8, k=0.075, cutoff_m=600.0)`: N×N matrix W_ij of velocity deficits (project pairwise displacement onto wind vector; only downwind pairs within cutoff get nonzero deficit)
   - Pure NumPy, no Qiskit needed here.
3. `core/quantum_hamiltonian.py` — Ising cost Hamiltonian for N=16 grid (4×4):
   - `build_ising(wake_matrix, wind_speeds, K=4)`: returns (h: linear coeffs, J: quadratic matrix) with x_i -> (I-Z_i)/2 mapping
   - Turbine-count penalty: λ_turb * (Σx_i - K)^2, λ auto-calibrated = 1.5 * max|W_ij|
   - Proximity penalty for pairs closer than 5D (600 m)
   - J must be symmetric, zero diagonal.
4. `tests/test_physics.py` — pytest: bins sum to 100%; deficit decreases with x;
   J symmetric + zero diagonal; 2×2 toy grid ground state matches brute force.

## Constraints
- Python 3.12, NumPy/SciPy only (Qiskit comes in Sprint 2). No fake data — the wind
  rose must be a documented realistic distribution, wake math must be the real Jensen equation.
- Small, clean modules. No drive-by refactors.

## Done when
- `pytest tests/test_physics.py -v` passes 100%.
- A demo script prints the 4×4 grid's W matrix heatmap values and the top-3
  brute-force layouts for K=4 (sanity: they avoid downwind shadowing).

## Verify command
`cd /home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype && python -m pytest tests/test_physics.py -v`

## Report back
DONE + test count + the 3 best brute-force layouts (bitstrings) for K=4.

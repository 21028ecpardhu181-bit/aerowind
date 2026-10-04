# SPRINT 2 BRIEF — Warm-started QAOA with K-preserving XY mixer (the quantum core)

## Objective
Build the heart of AeroQuantum-Wind: a warm-started QAOA that goes BEYOND vanilla QAOA.
This is what makes the team unique vs other hackathon teams. Read
`docs/AEROQUANTUM_MASTER_EXPLAINER_FOR_TEAM.md` and `briefs/NIGHT_SHIFT_PLAN.md` first.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`
Sprint 1 deliverables exist: `core/aerodynamics.py`, `core/quantum_hamiltonian.py`,
`data/anantapur_wind_rose_16bin.json`. USE them — do not rewrite.

## Environment
- Qiskit 2.5.2 + qiskit-aer 0.17.2 are installed in `~/.qenv` (use `~/.qenv/bin/python`).
- Use MODERN APIs only: `qiskit.circuit.QuantumCircuit`, `qiskit_aer.AerSimulator`,
  `qiskit.primitives.SamplerV2` (or StatevectorSampler for speed). NO deprecated
  `qiskit.algorithms` imports.

## Deliverables (`core/` + `tests/`)
1. `core/wsqaoa.py` — Warm-started QAOA:
   - `continuous_relaxation(h, J, K)`: solve the relaxed QP (c_i in [0,1]) with
     SciPy (SLSQP or COBYLA) minimizing the Ising energy + turbine-count penalty.
     Return c* vector.
   - `warm_start_angles(c)`: θ_i = 2*arcsin(sqrt(clip(c_i,0,1))) per Egger et al. 2021.
   - `build_ws_qaoa(h, J, K, p=2, thetas)`: circuit with
     * init: RY(θ_i) on each qubit (NOT Hadamard — this is the warm start)
     * cost unitary: RZZ(2*γ*J_ij) for each coupled pair + RZ(2*γ*h_i)
     * **XY mixer** (K-preserving): for each edge (i,j): exp(-i*β*(X_iX_j + Y_iY_j)/2)
       — implement as: H on both, CNOT, RZ, CNOT, H pattern OR use
       `qiskit.circuit.library.RXX`/`RYY` combined. The mixer must preserve
       Hamming weight (turbine count K). Start from a Dicke-like initial state
       OR from the warm-start state projected to weight K.
     * measure all qubits.
   - `optimize(h, J, K, p=2, shots=2048, maxiter=50)`: COBYLA loop over (γ,β),
     SamplerV2/AerSimulator, return best bitstring, energy, full counts, runtime.
   - Warm-start the (γ,β) optimizer at small angles (γ≈0.1, β≈0.1) — near the
     relaxed solution.
2. `core/post_processor.py`:
   - `repair(bitstring, K, W)`: 1-opt greedy — while weight != K, add/drop the
     turbine with best marginal energy change. Guarantee 100% valid output.
   - `aep_kwh(layout, wind_rose, rated_power_kw=3000)`: annual energy production
     from Jensen deficits (P ∝ v³).
3. `tests/test_wsqaoa.py`:
   - XY mixer preserves Hamming weight (run mixer-only circuit, assert all shots
     have weight K).
   - Warm-start thetas in [0, π].
   - On the 4×4 grid with K=4: QAOA finds a layout within 5% of brute-force
     optimum energy (use Sprint 1's brute-force as reference).
   - Repair guarantees weight K on random invalid bitstrings.

## Constraints
- 16 qubits max. p=2 (keep depth sane). 2048 shots.
- NO fake data: energies from the real Jensen W matrix.
- If COBYLA is slow (>30s), reduce maxiter to 30 and note it (Hour-12 fallback).

## Done when
- `pytest tests/test_wsqaoa.py -v` passes.
- Demo: print best layout bitstring, its AEP, wake loss %, and runtime.

## Verify command
`cd /home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype && ~/.qenv/bin/python -m pytest tests/test_wsqaoa.py -v`

## Report back
DONE + best bitstring + AEP (GWh) + wake loss % + runtime (s).

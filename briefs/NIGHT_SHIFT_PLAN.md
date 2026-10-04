# AEROQUANTUM-WIND — NIGHT SHIFT MASTER PLAN
**Source of truth:** AeroQuantum_Wind_3_9eqg.pdf (10 slides) + BUILD_PLAN_24H.md
**Team:** GENZ CREATORS — K. Satish Kumar (Lead), R.M. Bhanu, K. Bindhu
**Deadline:** Morning Oct 4 (user wakes) → hackathon Oct 8-9
**Rules:** LOCAL ONLY. No deploys. No pushes to main. No GitHub repo creation by me.

## What makes us unique (from the PDF — these are the moats)
1. Warm-started QAOA (R_y(θ) init from continuous relaxation, Egger et al. 2021) — NOT vanilla QAOA
2. K-preserving XY mixer — search stays in valid turbine-count subspace
3. Physics-informed cost — directional Jensen wake coupling in the Hamiltonian
4. Real NREL AP wind data → GPS-feasible layouts with AEP / wake-loss / revenue telemetry

## Build order (tonight)
- **Phase 1 — Quantum core (Python):** Jensen kernel ✓ (running) → Ising Hamiltonian ✓ (running) → WS-QAOA with XY mixer → classical baselines (PyGAD/DE/brute-force) → benchmark JSON proving QAOA beats GA
- **Phase 2 — API (FastAPI):** /optimize, /baseline, /compare, /wind-rose endpoints
- **Phase 3 — UI (Next.js 15 + Tailwind + Canvas 2D):** interactive site map, wind-rose dial, wake-plume canvas, before/after comparison slider, telemetry cards (AEP, wake loss %, revenue ₹), shot histogram
- **Phase 4 — Polish:** unique touches — animated wake cones, quantum-vs-classical race view, ₹ revenue ticker

## Skills to use (ours only)
- `frontend-design` — dashboard UI/UX
- `webapp-testing` / `verify-ui` — verify before calling done
- `tdd-workflow` — physics kernel tests
- `review-diff` — review agy output

## Reference research (read-only, no code copying)
- Existing GitHub: QAOA wind-farm / Qiskit optimization examples for API patterns only

## Fallback
- If agy credits exhaust → Muse implements directly (user pre-authorized).
- Hour-12 rule from build plan: if COBYLA too slow → warm-start with precomputed angles.

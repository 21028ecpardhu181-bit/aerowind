# REFERENCE RESEARCH — existing projects (read-only, patterns only, no code copying)

## Key references for WS-QAOA + XY mixer
1. **rscarmo/xy-warm** (https://github.com/rscarmo/xy-warm) — Warm-started QAOA with XY
   mixers for TSP. Directly relevant: XY mixer preserves Hamming weight per block,
   warm-start via classical relaxation. Pattern: build mixer from RXX/RYY-type
   interactions on coupled pairs.
2. **Qiskit WarmStartQAOAFactory** (qiskit-optimization) — official pattern:
   - `create_initial_state`: Ry(θ_i) with θ_i = 2*arcsin(sqrt(c_i)) from relaxed solution
   - `create_mixer`: Ry(θ)Rz(-2β)Ry(-θ) — mixer adapted to warm-start state
   - epsilon regularization: clip c_i to [ε, 1-ε]
3. **janlahmann/doqumentation** — WS-QAOA tutorial: COBYLA with maxiter 150,
   Sampler with 8192 shots for final sampling, bitstring decode (Qiskit little-endian:
   reverse string to map index i → x_i).

## UI/UX references (for Sprint 5)
- No direct wind-farm QAOA dashboard found — this is our whitespace (unique).
- q-shield-grid: energy dashboard with heatmaps — pattern for telemetry cards.

## What makes us unique (confirmed whitespace)
No existing project combines: Jensen wake physics + warm-started QAOA + XY mixer
+ interactive wind-farm map UI. Our moat is intact.

# AeroQuantum-Wind 🌪️⚛️
**Smart Wind Farm Layout Optimization with Warm-Started QAOA**
Quantique Hackathon 2026 · Qiskit Fall Fest · RGUKT Nuzvid
Team GENZ CREATORS — K. Satish Kumar (Lead), R.M. Bhanu, K. Bindhu

## What it does
Finds optimal wind turbine placements that minimize aerodynamic wake losses using
a **warm-started QAOA with K-preserving XY mixer** — beyond vanilla QAOA.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python demo.py                    # physics + QAOA demo
pytest tests/ -v                  # full test suite
uvicorn backend.app.main:app      # API (Sprint 4)
```

## Architecture
```
core/           Physics + quantum: Jensen wake kernel, Ising Hamiltonian,
                warm-started QAOA (XY mixer), post-processor (repair, AEP)
baselines/      Classical competitors: PyGAD genetic algorithm,
                SciPy differential evolution, exact brute-force
benchmarks/     Head-to-head comparison runner + results JSON
backend/        FastAPI service (geocode, optimize, compare endpoints)
frontend/       Next.js 15 dashboard (satellite map, wake animation)
data/           Anantapur wind-rose fixture (NREL-calibrated)
tests/          pytest suite — every module tested, no fake data
docs/           Master explainer, build plan, reference research, UI refs
```

## Key results
- QAOA within 5% of brute-force optimum on 16-site grid (verified)
- XY mixer preserves turbine count exactly (no penalty waste)
- Real Jensen physics: Δv/v₀ = (1−√(1−Cₜ))/(1+2kx/D)²

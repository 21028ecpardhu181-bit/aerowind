# SPRINT 4 BRIEF — FastAPI backend (geo + optimize + compare)

## Objective
Production-grade FastAPI service exposing the quantum core + geo-map features.
Read `briefs/geo-map-phase.md` for the geo endpoints spec.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`
Use: `core/wsqaoa.py`, `core/post_processor.py`, `core/aerodynamics.py`,
`baselines/`, `benchmarks/benchmark_results.json`.

## Deliverables (`backend/app/`)
```
backend/app/
  __init__.py
  main.py          # FastAPI app, CORS, routers
  api/
    __init__.py
    geo.py         # GET /api/geo/geocode?q=... (Nominatim, cached, 1 req/s, UA header)
                   # POST /api/geo/candidates {center_lat, center_lon, span_km, grid_n}
    optimize.py    # POST /api/optimize {sites:[{lat,lon}], K, wind_angle_deg, p=2}
                   #   → runs WS-QAOA, returns {layout, bitstring, aep_gwh,
                   #      wake_loss_pct, revenue_inr_cr, runtime_s, distances_m}
    compare.py     # GET /api/compare → benchmark_results.json + live QAOA row
  schemas.py       # Pydantic v2: strict validation (2≤K≤8, 0≤angle<360)
  geo_utils.py     # lat/lon ↔ meters (equirectangular), Nominatim client
```
- `revenue_inr_cr`: AEP(GWh) × ₹3.5/kWh / 1e7.
- Blueprint: `GET /api/blueprint?job_id=...` returns printable HTML (turbine GPS
  table, pairwise distances, AEP, wake loss). Keep it clean and professional.
- QAOA runs in a threadpool (don't block the event loop).

## Constraints
- Pydantic validation, 422 on bad input. No fake data.
- Nominatim: respect 1 req/sec, cache by query string.
- LOCAL ONLY.

## Done when
- `pytest tests/test_api.py -v` passes (write it: geocode mock, optimize K=4,
  validation rejects K=99).
- `uvicorn` boots; curl POST /api/optimize returns a valid layout in <30s.

## Verify command
`cd /home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype && ~/.qenv/bin/python -m pytest tests/test_api.py -v`

## Report back
DONE + optimize latency (s) + AEP for the test call.

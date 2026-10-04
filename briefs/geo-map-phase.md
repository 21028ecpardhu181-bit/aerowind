# GEO-MAP PHASE BRIEF — Real-world satellite siting with auto-placement + blueprint

## Vision (user's words)
User types a location name → satellite map fixes on it → user picks turbine count →
QAOA auto-places turbines optimally on the real map → shows power generation →
generates a blueprint with GPS coordinates, distances, everything.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`

## Backend (`backend/`, FastAPI)
1. `GET /api/geo/geocode?q=Anantapur,Andhra Pradesh` — Nominatim (OpenStreetMap)
   free API, no key needed. Return {lat, lon, display_name, boundingbox}.
   Cache results in-memory. Handle failures gracefully.
2. `POST /api/geo/candidates` — body {center_lat, center_lon, span_km, grid_n}:
   generate grid_n×grid_n candidate sites spanning span_km, return list of
   {id, lat, lon, x_m, y_m} where x_m/y_m are local meters (equirectangular
   projection around center). These feed the existing Jensen/QAOA pipeline.
3. `POST /api/geo/optimize` — body {candidates:[{lat,lon}], K, wind_angle}:
   run the Sprint-2 WS-QAOA pipeline on these real coordinates (convert lat/lon
   to meters for physics), return {layout:[{id,lat,lon}], aep_gwh, wake_loss_pct,
   revenue_inr_cr, distances_m: [[i,j,dist_m]...], blueprint_html}.
4. Blueprint: generate a clean HTML blueprint (printable) with site map SVG,
   turbine GPS table, pairwise distances, AEP, wake loss, revenue.

## Frontend (Sprint 5 UI — Leaflet)
- Leaflet 1.9 (CDN) with Esri World Imagery satellite tiles + OSM labels overlay.
- Search bar → geocode → fly to location, draw span rectangle.
- Turbine count slider (K=2..8), wind angle dial.
- "Optimize" → calls /api/geo/optimize → renders turbine markers on satellite map,
  wake cones as canvas overlay, click turbine → popup with GPS + power.
- Blueprint button → opens printable blueprint in new tab.
- Design: use `frontend-design` skill. Dark glass UI over satellite imagery.
  This must look STUNNING — it's the demo centerpiece.

## Constraints
- Nominatim: max 1 req/sec, set proper User-Agent header.
- Esri tiles: standard usage, attribute "Esri World Imagery".
- All physics in meters; GPS only for display/export.
- LOCAL ONLY. No deploys.

## Done when
- Search "Anantapur" → map shows satellite view of Anantapur.
- K=4 optimize → 4 turbines placed on map with wake cones, AEP shown.
- Blueprint HTML contains GPS table + distances + AEP.

## Report back
DONE + screenshot description + AEP for Anantapur K=4 demo.

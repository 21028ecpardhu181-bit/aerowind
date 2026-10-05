# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Active Task: Geotechnical Soil Risk Gating, Micro-Siting Setbacks, Village Boundary & Kilometres Auto-Fetch, and Multi-Dashboard Persistence
- **Branch**: `feature/engineering-setbacks-soil-autofetch`
- **Files Owned**:
  - `backend/app/gis/soil_client.py`
  - `backend/app/geo_engine.py`
  - `backend/app/db.py`
  - `backend/app/api/projects.py`
  - `src/components/workflow/Screen1Site.tsx`
  - `src/components/workflow/Screen2Config.tsx`
  - `src/components/dashboard/ProjectCard.tsx`
  - `src/components/dashboard/ProjectDashboard.tsx`
  - `src/components/dashboard/ProjectHero.tsx`
  - `src/services/api.ts`
  - `src/types/index.ts`
  - `src/App.tsx`
  - `tests/verify_geotechnical_setbacks_autofetch.py`

### Objectives & Completed Fixes:
1. **Soil Geotechnical Risk Gating & Critical Warning Banner**:
   - Upgraded `backend/app/gis/soil_client.py` to evaluate DNV-GL / IEC 61400-6 bearing capacity and multi-parameter hazard states (`SAFE`, `WARNING`, `CRITICAL_BLOCKED`).
   - In `Screen1Site.tsx`, if bearing capacity < 155 kPa or hazard is `CRITICAL_BLOCKED`, standard gravity base placement is prohibited with an explicit high-visibility warning banner.
   - The "Confirm Site & Proceed" button is disabled until the user selects Deep Bored Piled Foundation (30m rock sockets), guaranteeing geotechnical engineering safety before construction.
2. **Engineering Micro-Siting Setbacks & Environmental Exclusions**:
   - In `backend/app/geo_engine.py`, candidate micro-siting strictly enforces:
     - 500m Residential settlement buffer (IEC 61400 acoustic & shadow flicker setback).
     - 120m Riparian river/waterway buffer (ecological & flooding protection).
     - 200m Marine high-tide & saltwater spray erosion buffer.
     - 150m High-voltage transmission corridor setback (66kV-400kV anti-induction clearance).
     - 100m Logistics & heavy transport road corridor (80m blade transport and 800t crawler cranes).
   - Rendered dedicated "Micro-Siting Setbacks & Exclusions" cards in `Screen1Site.tsx` (Tab 4) and `Screen2Config.tsx`.
3. **Auto-Fetch Kilometres and Village Boundaries (Zero Manual Guessing)**:
   - Clicking on the map, searching a location, or snapping automatically queries OpenStreetMap Nominatim/Overpass, extracts the cadastral boundary polygon, computes the geodesic area in km² and equivalent radius $r = \sqrt{A/\pi}$, auto-updates the radius in kilometres, switches mode to `'village'`, and fetches live ISRIC soil and Open-Meteo wind telemetry.
4. **End-to-End Database & Multi-Dashboard Persistence**:
   - Added migrations in `backend/app/db.py` to persist `soil_bearing_capacity_kpa`, `usda_texture_class`, `foundation_type`, `soil_hazard_level`, and `environmental_notes` in `projects` SQLite table.
   - Extended `ProjectSummary`, `ProjectDetail`, `SiteInfo`, and `FarmConfig` in `src/types/index.ts`.
   - Updated `ProjectCard.tsx`, `ProjectDashboard.tsx`, and `ProjectHero.tsx` to display geotechnical soil bearing capacity, foundation engineering type, and micro-siting compliance notes.
5. **Verification & Quality Gates**:
   - `npm run build`: PASS (0 errors, built in 48s).
   - `tests/verify_geotechnical_setbacks_autofetch.py`: PASS (all desktop & mobile assertions green).
   - `tests/verify_project_dashboards_accuracy.py`: PASS (distinct counts, dynamic capacities).
   - `tests/verify_liquid_soil_village.py`: PASS (Apple Liquid Design, real soil/wind, free-form lasso, village cadastre).
   - Strictly 0 emojis in all code and UI.



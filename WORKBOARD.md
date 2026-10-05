# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Active Task: Village Boundary Auto-Loading, Strict Turbine Polygon Containment, Apple Liquid Glass UI, Zero Emojis & Accurate Dynamic Project Dashboards
- **Branch**: `feature/liquid-glass-village-boundaries-fix`
- **Files Owned**:
  - `src/components/workflow/Screen1Site.tsx`
  - `src/components/workflow/Screen2Config.tsx`
  - `src/components/workflow/Screen3Layout.tsx`
  - `src/components/workflow/Screen4Optimize.tsx`
  - `src/components/workflow/Screen5Inspect.tsx`
  - `src/components/workflow/Screen6Blueprint.tsx`
  - `src/components/dashboard/CreateNewProjectHero.tsx`
  - `src/components/dashboard/ProjectCard.tsx`
  - `src/components/dashboard/ProjectDashboard.tsx`
  - `src/components/dashboard/ProjectHero.tsx`
  - `src/components/dashboard/ProjectHome.tsx`
  - `src/App.tsx`
  - `src/services/api.ts`
  - `src/utils/geometry.ts`
  - `backend/app/geo_engine.py`
  - `backend/app/api/layout.py`
  - `backend/data/aeroquantum.db`

### Objectives & Completed Fixes:
1. **Turbine Outside Boundary Bug Fixed**: 
   - Root cause: unconstrained fallback generation `generateMockTurbines` placed turbines in a circle irrespective of polygon vertices.
   - Fix: Created `src/utils/geometry.ts` with `isPointInPolygon` (ray-casting), `pointToPolygonDistMeters` (safety setback), `generatePolygonEnclosedTurbines` (dense interior grid sampling + spatial thinning), and `ensureTurbinesInsideBoundary`. Integrated into `Screen3Layout`, `Screen5Inspect`, and `App.tsx`. 100% of turbines strictly reside within the user boundary with zero boundary leakage.
2. **Dynamic Project Metrics & Data Synchronization Fixed**:
   - Root cause: Screen 1 created projects before Screen 2 configured them, `onUpdateConfig` didn't synchronize `activeProject` or `projects` state list, `ProjectCard.tsx` hardcoded `* 2.5`, and older test runs flooded SQLite with duplicate rows.
   - Fix: Wired `handleUpdateConfig` in `App.tsx` to immediately synchronize `activeProject`, `projects` state, and `localStorage` with dynamic turbine counts and model ratings. Updated `ProjectCard.tsx`, `ProjectDashboard.tsx`, and `ProjectHero.tsx` to calculate MW capacity dynamically based on turbine model. Cleaned out test clutter from `backend/data/aeroquantum.db`.
3. **Village Boundary Cadastral Auto-Loading**:
   - Village borders automatically query and display official OSM cadastral borders upon any search or map tap. Normalized in `src/services/api.ts` and automated in `Screen1Site.tsx`.
4. **Zero Emojis Enforced**:
   - 100% of emojis removed across all frontend source files. Replaced with monochrome Lucide SVG icons (`Layers`, `Wind`, `Compass`, `ShieldCheck`, `MapPin`, etc.).
5. **Apple Liquid Glass Aesthetic**:
   - `CreateNewProjectHero.tsx` redesigned with deep backdrop blur (`backdrop-blur-3xl`), semi-translucent glass, specular rim highlights, prominent typography, and vibrant sunrise wind farm photography clearly visible through the glass.
6. **Test Verification**:
   - `tests/verify_project_dashboards_accuracy.py`: PASS (exit code 0). Verified unique turbine counts `{12, 14, 16, 18, 20}` and dynamic MW capacities.
   - `tests/verify_liquid_soil_village.py`: PASS (exit code 0). Verified Apple Liquid Glass, ISRIC soil telemetry, OSM village boundaries, Photoshop lasso polygon tool, and strict boundary containment.
   - `tests/verify_complete_flow.py`: PASS (exit code 0). Verified Screens 1 through 6 on both mobile (390px) and desktop (1280px).


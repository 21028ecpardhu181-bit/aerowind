# /boost — STOP UI REDESIGN. Fix the geospatial and engineering engine first.

The screenshot from the live site (aerowind.vercel.app/map) shows the core problem:
"12 requested → 1 feasible" — this is not a UI problem. The underlying geospatial state is broken.

The agent appears to be treating the map viewport/selection as the engineering area,
recalculating turbine positions from the current camera, and independently deciding
that only one turbine is feasible. That is why zooming changes turbine locations
and why "12 requested" becomes "1 feasible."

## CURRENT FAILURES
1. I request 12 turbines but the system displays 1.
2. The selected location is not the actual requested location.
3. I cannot reliably control the study-area size.
4. Turbines move when I zoom or change camera angle.
5. Turbine coordinates are not persistent.
6. The selected boundary and turbine positions are inconsistent.
7. Different locations behave differently instead of using one general algorithm.
8. The system appears to use the visible map viewport instead of a persistent geographic study area.
9. The optimizer is apparently optimizing a broken candidate set.
10. The current result cannot be trusted as an engineering simulation.

## FIRST: TRACE THE DATA

Find exactly where these values are created and passed:
location, latitude, longitude, study-area geometry, study-area radius,
polygon coordinates, requested turbine count, candidate turbine coordinates,
feasible turbine coordinates, optimized turbine coordinates, wind direction,
wind speed, terrain elevation, land constraints, wake model, QUBO/QAOA result.

Create ONE persistent project state:
```
Project
 ├── selectedLocation
 ├── studyAreaGeometry
 ├── studyAreaArea
 ├── requestedTurbineCount
 ├── turbineModel
 ├── windData
 ├── terrainData
 ├── constraints
 ├── candidatePositions[]
 └── optimizedPositions[]
```

The geographic coordinates must be the source of truth.

NEVER store turbine positions as: screen X/Y, percentage positions,
viewport-relative coordinates, CSS positions, image coordinates, map-pixel coordinates.

Every turbine must be stored as: T-01 → latitude, longitude, elevation.

Camera movement must NEVER modify these coordinates.
Zooming must only change: camera position, camera altitude, visual scale, level of detail.
It must NEVER regenerate turbine coordinates.

## LOCATION SELECTION

When user searches Rajahmundry, Bommuru, Hukkumpeta, Kanyakumari, or any location:
- Geocode the actual location and store its canonical coordinates.
- Do not use a hard-coded location.
- Do not use the current map center as the selected location after user has selected a place.
- Show: Selected location, Latitude, Longitude.
- Then move the camera to that exact location.
- The selected location must persist through every screen.

## STUDY AREA SELECTION (mandatory)

Implement TWO independent selection modes:

### 1. RADIUS
User selects a center point, then chooses: 1 km, 5 km, 10 km, 25 km, 50 km, 100 km, Custom.
The resulting circle must be geographic, not a visual circle around the screen.
If user selects 25 km, the actual geographic radius must be 25 km.

### 2. DRAW AREA
Allow drawing a polygon directly on the map with real lat/lon vertices.
Allow: tap to add point, drag/edit point, delete point, close polygon, clear, undo.
The polygon must remain fixed while zooming, panning, rotating.
Show: Area in km², Perimeter in km, Center lat/lon.

## MAP CAMERA

Use a real geospatial coordinate system. Camera and world independent from engineering data.
Support: 2D, 3D, tilt, orbit, north/south/east/west/top view.
When switching camera modes, all geographic objects remain fixed.

Test explicitly: Place T-01, record lat/lon, zoom in/out, rotate, tilt,
switch satellite→terrain→3D, return to original camera.
T-01 must remain at exactly the same geographic coordinate. Repeat for every turbine.

## REQUESTED TURBINE COUNT

If user requests 12 turbines, create a candidate problem for 12 turbines.
Do NOT silently replace 12 with 1.

Only two valid outcomes:
A. 12 feasible positions found. OR
B. Fewer than 12 feasible after real constraints. If B, explicitly show:
   "Requested: 12, Feasible: 7, Reason: Only 7 positions satisfy the current land, spacing and exclusion constraints."

Never silently display "12 requested → 1 turbine" without explaining why.
Allow changing: 1, 2, 5, 10, 12, 20, 50, 100, custom. System recalculates feasibility.

## CANDIDATE POSITION GENERATION

Build from the ACTUAL geographic study area. Consider: selected boundary, terrain,
slope, water, buildings/settlements, roads, protected areas, minimum spacing,
wind resource, existing infrastructure.

Each candidate gets: candidateId, latitude, longitude, elevation, land status,
slope, wind resource, distance to roads/settlements/boundary, constraint violations,
feasibility score.

Boundary comes FIRST. Candidate positions SECOND. Optimization THIRD.

## LAND / CONSTRAINT ENGINE

For every candidate evaluate: LAND, TERRAIN, SLOPE, WATER, BUILDINGS, SETTLEMENTS,
ROADS, PROTECTED AREAS, INFRASTRUCTURE, MINIMUM SPACING, WIND RESOURCE, WAKE INTERACTION.

Each candidate: FEASIBLE or REJECTED (with reason, e.g. "settlement setback",
"insufficient turbine spacing", "unsuitable slope"). Must be inspectable.

## OPTIMIZATION

Pipeline:
```
USER SELECTS LOCATION → USER DEFINES STUDY AREA → FETCH GEOSPATIAL DATA
→ GENERATE CANDIDATE POSITIONS → FILTER HARD CONSTRAINTS → BUILD WIND/WAKE MODEL
→ CREATE OPTIMIZATION PROBLEM → QUBO → QAOA/optimizer
→ SELECT OPTIMAL FEASIBLE POSITIONS → RETURN GEOGRAPHIC COORDINATES
→ RENDER THOSE EXACT COORDINATES
```
Optimizer must NEVER invent positions not in the candidate set.
If QAOA selects candidate 37, render candidate 37's exact lat/lon.

## WAKE MODEL

Wind direction must be geographic. For each turbine calculate downstream relationships
using geographic coordinates in a local metric system. Keep existing Jensen/Park
implementation if correct; fix the coordinate pipeline around it.

## 3D TERRAIN

Every final turbine must have known lat/lon/terrain elevation. Turbine base sits on terrain.
Camera: top view, tilted engineering view, close inspection, wide farm view.
Turbine model remains geographically anchored.

## MAP LABELS

When satellite selected, show clean geographic names (villages, towns, roads, rivers,
districts, landmarks). Do not cover engineering visualization. Site name = actual
selected location, never generic.

## MULTI-LOCATION TESTING

Test: Rajahmundry, Bommuru, Hukkumpeta, Kanyakumari, 2+ rural, 1+ hilly, 1+ coastal.
For each: select location, select area, request 1/5/12/larger turbines, zoom in/out,
rotate, switch terrain/satellite, run optimization. Same engine for every location.
No location-specific hard-coded coordinates.

## MANDATORY ACCEPTANCE TEST

1. Search Rajahmundry. 2. Select actual Rajahmundry location. 3. Draw study area.
4. System calculates actual area. 5. Request 12 turbines. 6. Generate candidates inside exact area.
7. Evaluate constraints. 8. Report actual feasible count. 9. Run optimization.
10. Optimizer selects valid coordinates. 11. Render all turbines. 12. Record every lat/lon.
13. Zoom max→close. 14. Rotate 360°. 15. Change satellite/terrain/3D.
16. Verify every turbine at exact same coordinate. 17. Export same coords to blueprint.
18. Reopen project. 19. Verify coordinates unchanged.
If any fail, do not move to UI polishing.

## IMPORTANT

Do NOT fix by: changing labels, changing numbers visually, hard-coding 12 turbines,
hard-coding locations, moving markers with CSS, generating fake coordinates,
drawing fake terrain, making screenshots look realistic.

Fix the underlying geographic data model and rendering pipeline.

Critical: do NOT force 12 turbines if only 1 is genuinely feasible. Correct behavior:
"Requested: 12 → Feasible: 1 → Only 1 position satisfies the selected constraints."
Then user can loosen study area/constraints and see count change.

After fixing, provide concise engineering report:
1. Root cause of wrong location
2. Root cause of 12 → 1
3. Root cause of turbine movement during zoom
4. Current coordinate system
5. Study-area implementation
6. Candidate-generation method
7. Constraint sources
8. Optimization pipeline
9. APIs/datasets used
10. Tests performed
11. Remaining limitations

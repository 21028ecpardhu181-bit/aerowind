# REALISM UPDATE (user requirement 2026-10-04 01:12 IST)

## Source photo
`docs/ui-refs/real-turbines-photo.jpg` — user's reference: real white 3-blade
turbines on terrain. This is the visual truth for turbine rendering.

## Turbine markers on the map — must look REAL
- NO cartoon dots or generic pins.
- Use `docs/ui-refs/turbine-marker-topdown` (AI-generated top-down turbine) as the
  Leaflet marker icon, sized ~48px, drop-shadow for depth.
- Canvas overlay draws the rotor blades ROTATING (3 blades, white with subtle
  shading) — rotation speed ∝ effective wind speed at that turbine.
- Tower shadow: soft ellipse offset downwind, sells the 3D feel on satellite imagery.
- Click/hover: popup card with turbine ID, GPS coords, individual power (MW),
  wake-affected vs clean status.

## Placement — coordinate-based + quantum
- Candidate sites and final layout are REAL GPS coordinates (lat/lon), not
  abstract grid cells.
- QAOA optimizes on meters-converted coordinates; results mapped back to GPS.
- Blueprint exports real coordinates + real inter-turbine distances in meters.

## Terrain awareness (stretch)
- If time permits: use Esri elevation or simple slope heuristic to prefer
  ridge/hilltop sites (like the photo — turbines on ridgelines catch more wind).
- Mark as stretch; coordinate-accurate placement is the must-have.

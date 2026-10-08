# SPRINT 5 BRIEF — Dashboard animation + polish (final UI)

## Objective
Take `frontend/index.html` (Leaflet satellite dashboard, works) and implement the
full animation system from `briefs/animation-spec.md` + `briefs/realism-update.md`.

## Project root
`/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/`
Reference images: `docs/ui-refs/` (dashboard ref, wake ref, real turbine photo,
turbine-marker-topdown.png — ALREADY copied to `frontend/assets/`).

## Deliverables (edit `frontend/index.html` + new `frontend/js/wind-fx.js` if needed)
1. **Wind particle system**: ~200 canvas streak particles flowing in the wind
   direction (from backend `wind_angle_deg`), cyan in clean air → amber/red inside
   wake cones. Respawn upwind. 60fps; reduce count if frame time > 25ms.
2. **Spinning turbine rotors**: draw 3 white blades per turbine on the canvas
   overlay, rotating at speed ∝ that turbine's effective wind speed
   (backend returns per-turbine `effective_mps` — add it to /api/optimize if missing).
   Waked turbines visibly slower.
3. **Wake cones**: translucent expanding cones downwind per Jensen
   (half-angle from k=0.075), alpha ∝ local deficit, additive blending.
4. **Wind direction dial**: interactive compass dial; rotating it re-routes all
   particles + wakes in real time (re-run optimize on release).
5. **Before/after wipe**: slider comparing baseline layout vs QAOA layout.
6. **Animated tickers**: AEP / wake-loss / revenue count up with easing on results.
7. **Mobile**: must work at 390px — controls collapse into bottom sheet.

## Constraints
- Use `frontend-design` skill for any new UI. Match the existing glass aesthetic.
- `verify-ui` skill: screenshot 390px + 1280px before done.
- No new backend endpoints unless strictly needed.

## Done when
- Open index.html against the running backend, search Anantapur, optimize K=4:
  turbines appear with spinning blades, wind streaks flow, wakes render,
  tickers animate, dial rotates the field.

## Report back
DONE + screenshots taken (paths) + any perf notes.

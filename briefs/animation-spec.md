# ANIMATION & VISUAL SPEC — must-match behaviors

## Wind flow animation (like the PDF)
- Canvas 2D particle system: ~200 wind streak particles flowing across the map in
  the prevailing wind direction. Particles spawn upwind, accelerate slightly through
  turbine gaps, decelerate + scatter inside wake cones.
- Wind direction dial rotates the entire flow field in real time (particles re-route).
- Streak color: cyan (#22d3ee) clean air → amber/red (#f59e0b/#ef4444) inside wakes.
- 60fps target; particle count auto-reduces on slow devices.

## Turbine animation
- Each placed turbine marker: 3-blade rotor drawn on canvas, rotating at speed
  proportional to its effective wind speed (waked turbines spin visibly slower —
  this TEACHES the wake effect without words).
- Blade rotation: requestAnimationFrame, ~15 RPM visual for clean-air turbines.

## Wake cones
- Translucent expanding cones downwind of each turbine, alpha gradient fading with
  distance (Jensen expansion: cone half-angle grows with k*x/D).
- Color intensity ∝ local velocity deficit. Overlapping cones blend additively.

## Transitions
- Optimize button: turbines "fly in" with staggered drop animation; old layout fades.
- Before/after slider: drag to wipe between baseline (red wakes) and optimized
  (green/clean) layouts.
- Number tickers: AEP/wake-loss/revenue count up with easing on new results.

## Reference images (in docs/ui-refs/)
- dashboard-satellite-ref: overall dashboard aesthetic (dark glass + satellite + cyan streaks)
- turbine-wake-ref: wake cone look (cyan clean → red turbulent)

## Skills
- `frontend-design`: layout, typography, color system from the refs above.
- `verify-ui`: screenshot at 390px and 1280px before calling done.
- If a repeated animation problem emerges → `skill-creator` to save a canvas-particle skill.

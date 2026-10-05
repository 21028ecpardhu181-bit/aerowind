# Study Notes - 2026-10-04 - AeroQuantum-Wind hackathon prototype
<!-- studying-run-start: 2026-10-04T11:36:06Z -->

Goal `goal_4668e9cd5af1`: build a working AeroQuantum-Wind prototype (warm-started QAOA + Jensen wake wind-farm layout optimizer, FastAPI backend, interactive map dashboard) for Quantique Hackathon Round 2, RGUKT Nuzvid, Oct 8–9, 2026. Team: GENZ CREATORS (Satish, R.M. Bhanu, K. Bindhu). Live at https://aerowind.vercel.app/.

Note on the study plan: the assigned task plan is a learning-science scaffold (teach mode, novice band, retrieval prompts, practice tasks). This goal is an outcome goal — a live hackathon build mid-crisis — not a skill to be taught. Per step rules, the plan is treated as weak scheduler metadata; this note is a research note, not a lesson. No numeric mastery estimate is made (fewer than three observed performances).

## Goal state as of today

- Overnight (2026-10-03/04) the prototype was delivered: physics kernel 12/12, warm-started QAOA 8/8 within 5% of optimal, 42/42 tests green, Cesium 3D pipeline, FastAPI backend. The user then lifted the local-only constraint: repo satish024-024/AEROWIND on GitHub, imported into Vercel themselves, live at aerowind.vercel.app.
- Two engine rebuilds landed 2026-10-04 ~09:20 and ~09:42 UTC (scale-adaptive geographic engine in `backend/app/geo_engine.py`; engineering rebuild with GLB turbine asset + 5-class feasibility mask via POST /api/geo/feasibility), each with all-green test claims.
- At ~10:05 UTC 2026-10-04 the user falsified the underlying geospatial state from their phone — not a UI problem: positions appeared regenerated from the camera, zoom changed turbine locations, the selected location wasn't the requested one, and "12 requested" became "1 feasible" with no explanation. This supersedes the in-session validation claims (20/20 placed, 0 boundary violations, coordinate permanence).
- Standing directive (user's, adopted verbatim): STOP UI redesign until the engine passes acceptance tests. Fix first, trace-the-data-first. Geographic coordinates are the source of truth (T-01 → lat/lon/elevation; never screen/viewport/pixel coordinates; camera movement must NEVER regenerate coordinates). Pipeline order: boundary first, candidates second, optimization third. Honest feasible counts only ("Requested: 12 → Feasible: 1" with the reason), never force turbines to fake a demo.
- BOOST_DIRECTIVE.md (8428 bytes) sits in the AEROWIND project root (this goal workspace): the user's 10-failure trace + data model + 19-step acceptance criteria, written for an Antigravity session via `/boost`.
- Open decision: who runs /boost — the user pastes `/boost` into antigravity.google.com → Satish-VM themselves, or says "you do it" and Muse fixes the engine directly. Offered in main chat 2026-10-04T10:15:41; still open at end of window.

## Today's new finding (from this study)

**An agent self-certification post-dates the user's falsification.** `TEST_READY.md` (mtime 2026-10-04 11:03 UTC — after the user's ~10:05 UTC diagnosis) certifies "ALL TEST SUITES VERIFIED AND PASSING (100% GREEN)": 42/42 pytest, Bommuru boundary check, 6-screen E2E, 5-city geographic pipeline, Cesium milestone. Its claims include:

- "20 requested ➔ 20 placed, min spacing 600.0 m, 0 perimeter violations" for Bommuru, Rajahmundry, Jaisalmer, Hukkumpeta, Kanyakumari;
- "Coordinate persistence across Leaflet map zoom (10 to 14): coordinates invariant to 6 decimal places";
- "Small-Area Honest Capacity: Bommuru 1 km circle, 20 requested ➔ 7 placed, headline '20 requested · 7 feasible', never collapses to 1."

These re-assert exactly the claims the user falsified from their phone (zoom moved turbines; live result "12 requested → 1 feasible"). Per the user's evidence bar — an agent's own test suite is a claim, the user's device verdict is proof — TEST_READY.md is an unproven agent claim, not verification. The fact that the green suite doesn't reproduce the user's observed 12→1 live failure is itself diagnostic: the test environment is not exercising the broken path (likely local vs. Vercel-served frontend, or a fixture that sidesteps the geocoding/pipeline ordering bug). PROJECT.md (10,762 bytes, updated 10:51 UTC) and TEST_INFRA.md (21,150 bytes, updated 11:02 UTC) are the same post-diagnosis artifacts; read them before trusting any claim in them.

## What the bar is now (for later work)

- No fix, rebuild, or green banner on this goal counts as done until the user's phone verdict on the acceptance criteria in BOOST_DIRECTIVE.md says so. Desktop-viewport checks, pytest, Playwright, and deployed-asset reads are preparation.
- The acceptance test must be run against the live site (aerowind.vercel.app), not just the local 127.0.0.1:8000 backend, since the live site is where the user observed the failure.
- Boundary for Muse on this goal: Muse may not re-study/rewrite the engine while the Antigravity session owns the files — one owner per file (WORKBOARD.md); the /boost choice stays with the user.
- Known pending items (not new): re-upload the correct 21,872-byte wind_turbine.glb (live copy corrupted at 29,089 bytes); live wind-data APIs not wired for arbitrary GPS coordinates (calibrated fixture for Anantapur, standard profiles elsewhere); user's Satish-VM keepalive running.

## Unknowns to learn without interrogating

- Whether the user already saw TEST_READY.md's claims via their Antigravity session (they see that session from their phone; I cannot).
- Whether the user has run the acceptance steps yet, and which failure fires first on the live site.
- Which implementation the user picks for /boost (their paste vs. "you do it").

## Already Covered in Main Chat

- The user diagnosed the geospatial engine as fundamentally broken (~10:05 UTC 2026-10-04): camera-regenerated positions, zoom changing turbine locations, wrong location selected, "12 requested → 1 feasible" unexplained.
- Muse offered the /boost handoff: user pastes `/boost` into their Antigravity session, or says "you do it" for Muse to fix the engine directly (10:15 UTC 2026-10-04) — choice still open.
- At 10:32 UTC the user asked "Is instance stopped?", approved the restart, and Satish-VM went live at antigravity.google.com.
- Two Antigravity account switches on 2026-10-04 (~04:52 and ~11:24 UTC); after the latest, Satish-VM is live and the 15-minute keepalive is on.
- STOP-UI-redesign directive and the coordinate-source-of-truth rules were communicated back to the user this morning.

## Research Trajectory

- *External sources viewed*: none — this study needed local/user evidence, not the web. The topic is this user's project state; no scaffold or publication applies. Browser search was judged marginal and skipped.
- *Prior trajectories reviewed*: goal record (`user_goal.get` for goal_4668e9cd5af1) — active, outcome kind, slug aeroquantum-wind-hackathon-prototype, zero timeline updates since creation 2026-10-03T19:22:35Z, zero briefings recorded, zero suggestions. No prior study notes exist under `workspace/goals/aeroquantum-wind-hackathon-prototype/agent_notes/` (directory empty).
- *Goal workspace inspected*: listing of `briefs/` (9 sprint/phase Markdown docs, none are Letters); read TEST_READY.md in full (2026-10-04 11:03 UTC self-certification, 100%-green claims detailed above); read BOOST_DIRECTIVE.md head (user's failure trace, data model, coordinate-source-of-truth rules); confirmed PROJECT.md / TEST_INFRA.md mtimes post-date the user's 10:05 UTC diagnosis but did not read them (marginal — flagged for next pass if claims surface).
- *Repetition search*: grep-style listing of `agent_notes/` (empty — no prior notes) and `briefs/` filenames (sprint1–sprint5, geo-map-phase, animation-spec, realism-update, NIGHT_SHIFT_PLAN — all sprint-phase docs, none covering TEST_READY.md's post-diagnosis certification or the verification-gap finding). Briefing history on the goal record is empty; no prior Letter exists to collide with.
- *User context and memory*: genz-creators.md group page (verified-extraction summary current through 2026-10-04 10:52 UTC — engine diagnosis, /boost choice, GLB corruption, keepalive); MEMORY.md (security sprint, account switches, Turbo mode, verification boundaries).
- *Connected user data*: not consulted — goal is code/project state, fully available in the workspace; no wearables/calendar signal relevant.
- *Image references checked*: none staged this run.
- *Scaffolds and support tactics*: category is null for this goal; no registry tactics applied. The assigned teach-mode plan was deliberately not preserved as a lesson shape (outcome goal, not a learning goal).
- *Fleet learnings*: `muse.learnings_search` called with three goal-specific queries; exchange returned `fleet_learning_consumption_disabled` — no lessons available this run. Proceeded on local evidence alone.
- *Searches skipped or unavailable*: web search (no applicable external source for this user's project state); fleet exchange (disabled); PROJECT.md/TEST_INFRA.md full reads (flagged, marginal this pass).

"""
backend/app/api/optimize.py — Quantum WS-QAOA Micro-Siting Optimization & Blueprint Endpoints.

Endpoints:
1. POST /api/optimize
   - Runs Warm-Started QAOA with K-preserving XY mixer in a threadpool.
   - Physics-grounded Jensen aerodynamic wake model & Ising cost Hamiltonian.
   - Returns {job_id, layout, bitstring, aep_gwh, wake_loss_pct, revenue_inr_cr, runtime_s, distances_m, blueprint_url}.
2. POST /api/geo/optimize
   - Alias for POST /api/optimize to support geo-map-phase specification.
3. GET /api/blueprint?job_id=...
   - Returns printable, professional HTML engineering blueprint with site map SVG,
     turbine GPS table, pairwise distances, AEP, wake loss, and revenue.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import html
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse
import numpy as np

from core.aerodynamics import pairwise_wake_matrix
from core.post_processor import compute_aep_summary, repair
from core.quantum_hamiltonian import build_ising
from core.wsqaoa import optimize

try:
    from backend.app.geo_utils import compute_pairwise_distances, lat_lon_to_meters
    from backend.app.schemas import (
        OptimizeRequest,
        OptimizeResponse,
        TurbinePlacement,
    )
except ImportError:
    from app.geo_utils import compute_pairwise_distances, lat_lon_to_meters
    from app.schemas import (
        OptimizeRequest,
        OptimizeResponse,
        TurbinePlacement,
    )

router = APIRouter(prefix="", tags=["optimize"])

# In-memory storage for optimization jobs and blueprint rendering
JOB_STORE: Dict[str, Dict[str, Any]] = {}

# Most recent live QAOA run telemetry for /api/compare
_LATEST_QAOA_RUN: Optional[Dict[str, Any]] = None


def get_latest_qaoa_run() -> Optional[Dict[str, Any]]:
    """Returns the telemetry of the most recent live QAOA execution."""
    return _LATEST_QAOA_RUN


def set_latest_qaoa_run(run_data: Dict[str, Any]) -> None:
    """Updates the telemetry of the most recent live QAOA execution."""
    global _LATEST_QAOA_RUN
    _LATEST_QAOA_RUN = run_data


def generate_blueprint_html(job_data: Dict[str, Any]) -> str:
    """
    Renders an engineering-grade, printable HTML blueprint for a completed turbine layout.
    Features:
    - Clean responsive layout with dark glass / blueprint styling and @media print support.
    - SVG layout map diagram with turbine markers and wind direction vector.
    - Turbine GPS coordinate table.
    - Pairwise distance and 5D clearance verification table.
    - Comprehensive AEP, wake loss, and revenue summary cards.
    """
    job_id = html.escape(str(job_data.get("job_id", "")))
    created_at = html.escape(str(job_data.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))))
    k_val = int(job_data.get("K", 4))
    wind_angle = float(job_data.get("wind_angle_deg", 270.0))
    aep_gwh = float(job_data.get("aep_gwh", 0.0))
    wake_loss_pct = float(job_data.get("wake_loss_pct", 0.0))
    revenue_inr_cr = float(job_data.get("revenue_inr_cr", 0.0))
    runtime_s = float(job_data.get("runtime_s", 0.0))
    bitstring = html.escape(str(job_data.get("bitstring", "")))
    layout: List[Dict[str, Any]] = job_data.get("layout", [])
    distances_m: List[List[float]] = job_data.get("distances_m", [])

    # Calculate SVG layout bounds
    xs = [t["x_m"] for t in layout] if layout else [0.0]
    ys = [t["y_m"] for t in layout] if layout else [0.0]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    padding = max(150.0, max(max_x - min_x, max_y - min_y) * 0.15)
    view_min_x = min_x - padding
    view_min_y = min_y - padding
    view_w = max(400.0, (max_x - min_x) + 2 * padding)
    view_h = max(400.0, (max_y - min_y) + 2 * padding)

    # Invert SVG Y axis so North is up
    svg_markers = []
    for idx, t in enumerate(layout, 1):
        x = t["x_m"]
        y = t["y_m"]
        svg_y = view_min_y + view_h - (y - view_min_y)
        svg_markers.append(f"""
            <g transform="translate({x:.1f}, {svg_y:.1f})">
                <circle r="14" fill="#0284c7" fill-opacity="0.25" stroke="#38bdf8" stroke-width="2" />
                <circle r="5" fill="#38bdf8" />
                <text x="18" y="5" font-family="monospace" font-size="12" font-weight="bold" fill="#0f172a">T{idx} (#{t['id']})</text>
            </g>
        """)
    markers_markup = "\n".join(svg_markers)

    # Wind direction arrow calculation (wind direction angle in meteorological deg)
    wind_rad = np.radians(wind_angle)
    # Wind blowing towards: dx = -sin(angle), dy = -cos(angle)
    arrow_dx = -np.sin(wind_rad) * 40.0
    arrow_dy = np.cos(wind_rad) * 40.0

    # Build GPS table rows
    gps_rows = []
    for idx, t in enumerate(layout, 1):
        gps_rows.append(f"""
            <tr>
                <td style="font-weight: 600; color: #0284c7;">T{idx}</td>
                <td>#{t['id']}</td>
                <td>{t['lat']:.7f}°</td>
                <td>{t['lon']:.7f}°</td>
                <td>{t['x_m']:+.1f} m</td>
                <td>{t['y_m']:+.1f} m</td>
                <td><span class="status-badge status-active">Active</span></td>
            </tr>
        """)
    gps_rows_markup = "\n".join(gps_rows)

    # Build pairwise distances table rows
    dist_rows = []
    for pair in distances_m:
        u, v, dist = int(pair[0]), int(pair[1]), float(pair[2])
        is_safe = dist >= 600.0
        badge_class = "status-safe" if is_safe else "status-warn"
        badge_label = "≥ 5D Safe" if is_safe else "< 5D Warning"
        t_a_label = f"T{u + 1}"
        t_b_label = f"T{v + 1}"
        dist_rows.append(f"""
            <tr>
                <td style="font-weight: 600;">{t_a_label} ↔ {t_b_label}</td>
                <td>{dist:.1f} m</td>
                <td><span class="status-badge {badge_class}">{badge_label}</span></td>
            </tr>
        """)
    dist_rows_markup = "\n".join(dist_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AeroQuantum-Wind Blueprint — Job {job_id}</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --primary: #0284c7;
            --primary-light: #e0f2fe;
            --border-color: #e2e8f0;
            --success: #16a34a;
            --warning: #d97706;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.5;
            padding: 32px 24px;
        }}
        .blueprint-container {{
            max-width: 1080px;
            margin: 0 auto;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
            padding: 40px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 20px;
            margin-bottom: 28px;
        }}
        .header-title h1 {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--text-main);
        }}
        .header-title p {{
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .header-meta {{
            text-align: right;
            font-family: monospace;
            font-size: 13px;
            color: var(--text-muted);
        }}
        .print-btn {{
            background: var(--primary);
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
            transition: background 0.2s;
        }}
        .print-btn:hover {{ background: #0369a1; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background: #f1f5f9;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
        }}
        .metric-label {{
            font-size: 12px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 800;
            color: var(--primary);
            margin-top: 4px;
        }}
        .metric-sub {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .map-section {{
            margin-bottom: 32px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: #f8fafc;
            overflow: hidden;
        }}
        .svg-container {{
            width: 100%;
            height: 380px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        svg {{ width: 100%; height: 100%; }}
        .table-section {{
            margin-bottom: 32px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            color: var(--text-muted);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        tr:last-child td {{ border-bottom: none; }}
        .status-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .status-active {{ background: #dcfce7; color: var(--success); }}
        .status-safe {{ background: #dcfce7; color: var(--success); }}
        .status-warn {{ background: #fef3c7; color: var(--warning); }}
        .footer {{
            border-top: 1px solid var(--border-color);
            padding-top: 20px;
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            body {{ padding: 0; background: #ffffff; }}
            .blueprint-container {{ border: none; box-shadow: none; padding: 20px; }}
            .no-print {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    <div class="blueprint-container">
        <header class="header">
            <div class="header-title">
                <h1>AeroQuantum-Wind Layout Blueprint</h1>
                <p>WS-QAOA Quantum Micro-Siting Optimization Specification</p>
            </div>
            <div class="header-meta">
                <div><strong>Job ID:</strong> {job_id}</div>
                <div><strong>Date:</strong> {created_at}</div>
                <div class="no-print">
                    <button class="print-btn" onclick="window.print()">Print / Export PDF</button>
                </div>
            </div>
        </header>

        <section class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Turbine Count</div>
                <div class="metric-value">{k_val} Units</div>
                <div class="metric-sub">Rated Capacity: {k_val * 3} MW</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Annual Yield (AEP)</div>
                <div class="metric-value">{aep_gwh:.2f} GWh</div>
                <div class="metric-sub">Jensen Wake Loss: {wake_loss_pct:.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Est. Revenue</div>
                <div class="metric-value">₹{revenue_inr_cr:.2f} Cr</div>
                <div class="metric-sub">Tariff ₹3.50/kWh / annum</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Quantum Solver</div>
                <div class="metric-value">{runtime_s:.2f}s</div>
                <div class="metric-sub">WS-QAOA (p=2, XY-Mixer)</div>
            </div>
        </section>

        <section class="map-section">
            <div class="svg-container">
                <svg viewBox="{view_min_x:.1f} {view_min_y:.1f} {view_w:.1f} {view_h:.1f}" preserveAspectRatio="xMidYMid meet">
                    <!-- Grid background lines -->
                    <defs>
                        <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
                            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#e2e8f0" stroke-width="1"/>
                        </pattern>
                        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#0284c7" />
                        </marker>
                    </defs>
                    <rect x="{view_min_x}" y="{view_min_y}" width="{view_w}" height="{view_h}" fill="url(#grid)" />

                    <!-- Wind direction indicator -->
                    <g transform="translate({view_min_x + view_w - 70:.1f}, {view_min_y + 60:.1f})">
                        <circle r="28" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5" />
                        <line x1="0" y1="0" x2="{arrow_dx:.1f}" y2="{arrow_dy:.1f}" stroke="#0284c7" stroke-width="3" marker-end="url(#arrow)" />
                        <text x="0" y="-32" font-family="monospace" font-size="10" font-weight="bold" fill="#64748b" text-anchor="middle">WIND {wind_angle:.0f}°</text>
                    </g>

                    <!-- Placed Turbines -->
                    {markers_markup}
                </svg>
            </div>
        </section>

        <section class="table-section">
            <h2 class="section-title">Turbine GPS Placement Matrix</h2>
            <table>
                <thead>
                    <tr>
                        <th>Turbine</th>
                        <th>Site ID</th>
                        <th>Latitude</th>
                        <th>Longitude</th>
                        <th>Local X</th>
                        <th>Local Y</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {gps_rows_markup}
                </tbody>
            </table>
        </section>

        <section class="table-section">
            <h2 class="section-title">Pairwise Separation & 5D Aerodynamic Clearance (≥ 600m)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Turbine Pair</th>
                        <th>Physical Distance</th>
                        <th>5D Rotor Clearance</th>
                    </tr>
                </thead>
                <tbody>
                    {dist_rows_markup}
                </tbody>
            </table>
        </section>

        <footer class="footer">
            <div>Bitstring: <code>{bitstring}</code></div>
            <div>AeroQuantum-Wind Hackathon Prototype — Autonomous Quantum Micro-Siting</div>
        </footer>
    </div>
</body>
</html>
"""


def _sync_optimize_worker(
    coords: np.ndarray,
    site_ids: List[int],
    site_lats: List[float],
    site_lons: List[float],
    K: int,
    wind_angle_deg: float,
    p: int,
) -> Dict[str, Any]:
    """
    Synchronous compute worker for WS-QAOA optimization.
    Executed inside an asyncio thread pool to keep the event loop non-blocking.
    """
    start_time = time.time()
    N = coords.shape[0]

    # 1. Aerodynamic wake coupling matrix W
    D = 120.0       # Rotor diameter in meters
    Ct = 0.8        # Thrust coefficient
    k_wake = 0.075  # Wake decay constant
    cutoff = 600.0  # 5D proximity threshold

    W = pairwise_wake_matrix(
        coords,
        wind_angle_deg=wind_angle_deg,
        D=D,
        Ct=Ct,
        k=k_wake,
        cutoff_m=cutoff,
        use_wake_cone=True,
    )

    # 2. Build QAOA Ising Cost Hamiltonian (h, J)
    h, J = build_ising(
        W,
        wind_speeds=8.42,
        K=K,
        coords=coords,
        min_distance_m=cutoff,
    )

    # 3. WS-QAOA classical-quantum optimization
    best_bs, best_e, counts, opt_rt = optimize(
        h,
        J,
        K=K,
        p=p,
        shots=1024,
        maxiter=25,
        W=W,
    )

    # 4. Guarantee weight K via greedy repair
    final_bitstring = repair(best_bs, K=K, W=W)
    total_runtime = time.time() - start_time

    # 5. Extract chosen active turbine layout
    active_indices = [i for i, bit in enumerate(final_bitstring) if bit == "1"]
    active_coords = coords[active_indices]

    # Compute pairwise wake deficit on active turbines for effective wind speeds
    W_active = pairwise_wake_matrix(
        active_coords,
        wind_angle_deg=wind_angle_deg,
        D=D,
        Ct=Ct,
        k=k_wake,
        cutoff_m=cutoff,
        use_wake_cone=True,
    )
    v0_freestream = 8.42  # Freestream wind speed (m/s)

    layout_items: List[Dict[str, Any]] = []
    for local_i, idx in enumerate(active_indices):
        incoming_deficits = W_active[:, local_i]
        deficit_rss = float(np.sqrt(np.sum(incoming_deficits ** 2)))
        effective_mps = round(float(v0_freestream * max(0.0, 1.0 - deficit_rss)), 2)
        layout_items.append({
            "id": site_ids[idx],
            "lat": site_lats[idx],
            "lon": site_lons[idx],
            "x_m": round(float(coords[idx, 0]), 2),
            "y_m": round(float(coords[idx, 1]), 2),
            "effective_mps": effective_mps,
        })

    # 6. Pairwise distances
    distances_m = compute_pairwise_distances(active_coords)

    # 7. AEP Telemetry
    aep_summary = compute_aep_summary(final_bitstring, coords=coords)
    aep_gwh = round(float(aep_summary["aep_gwh"]), 4)
    wake_loss_pct = round(float(aep_summary["wake_loss_pct"]), 4)

    # 8. Revenue calculation: AEP(GWh) * 1e6 kWh * 3.5 INR / 1e7 = AEP * 0.35
    revenue_inr_cr = round((aep_gwh * 1e6 * 3.5) / 1e7, 4)

    return {
        "layout": layout_items,
        "bitstring": final_bitstring,
        "best_energy": float(best_e),
        "aep_gwh": aep_gwh,
        "wake_loss_pct": wake_loss_pct,
        "revenue_inr_cr": revenue_inr_cr,
        "runtime_s": round(total_runtime, 4),
        "distances_m": distances_m,
        "W": W,
    }


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Run WS-QAOA quantum turbine layout optimization",
    description="Optimizes wind turbine placement on candidate GPS sites using Warm-Started QAOA with XY mixer.",
)
async def run_optimization(req: OptimizeRequest) -> OptimizeResponse:
    sites = req.resolved_sites
    N = len(sites)
    if N < req.K:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Candidate sites count ({N}) must be >= target turbine count K ({req.K}).",
        )

    # Resolve metric coordinates
    # If all sites have x_m and y_m specified, use them directly
    has_xy = all(s.x_m is not None and s.y_m is not None for s in sites)
    if has_xy:
        coords = np.array([[s.x_m, s.y_m] for s in sites], dtype=np.float64)
    else:
        # Equirectangular projection relative to geographic center
        center_lat = float(np.mean([s.lat for s in sites]))
        center_lon = float(np.mean([s.lon for s in sites]))
        coords_list = []
        for s in sites:
            x, y = lat_lon_to_meters(s.lat, s.lon, center_lat, center_lon)
            coords_list.append([x, y])
        coords = np.array(coords_list, dtype=np.float64)

    site_ids = [s.id if s.id is not None else i for i, s in enumerate(sites)]
    site_lats = [s.lat for s in sites]
    site_lons = [s.lon for s in sites]
    angle = req.resolved_angle

    # Execute QAOA optimization in threadpool (non-blocking for asyncio event loop)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _sync_optimize_worker,
        coords,
        site_ids,
        site_lats,
        site_lons,
        req.K,
        angle,
        req.p,
    )

    job_id = uuid.uuid4().hex[:12]
    blueprint_url = f"/api/blueprint?job_id={job_id}"

    job_record = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "K": req.K,
        "wind_angle_deg": angle,
        "layout": result["layout"],
        "bitstring": result["bitstring"],
        "best_energy": result["best_energy"],
        "aep_gwh": result["aep_gwh"],
        "wake_loss_pct": result["wake_loss_pct"],
        "revenue_inr_cr": result["revenue_inr_cr"],
        "runtime_s": result["runtime_s"],
        "distances_m": result["distances_m"],
        "blueprint_url": blueprint_url,
    }

    # Generate blueprint HTML
    blueprint_html = generate_blueprint_html(job_record)
    job_record["blueprint_html"] = blueprint_html

    # Save to JOB_STORE
    JOB_STORE[job_id] = job_record

    # Update latest live QAOA run for /api/compare
    set_latest_qaoa_run({
        "angle": angle,
        "K": req.K,
        "method": "qaoa",
        "best_energy": round(result["best_energy"], 6),
        "aep_gwh": round(result["aep_gwh"], 4),
        "wake_loss_pct": round(result["wake_loss_pct"], 4),
        "runtime_s": round(result["runtime_s"], 4),
        "is_live": True,
    })

    return OptimizeResponse(
        job_id=job_id,
        layout=[TurbinePlacement(**t) for t in result["layout"]],
        bitstring=result["bitstring"],
        aep_gwh=result["aep_gwh"],
        wake_loss_pct=result["wake_loss_pct"],
        revenue_inr_cr=result["revenue_inr_cr"],
        runtime_s=result["runtime_s"],
        distances_m=result["distances_m"],
        blueprint_url=blueprint_url,
        blueprint_html=blueprint_html,
    )


# Alias route to satisfy geo-map-phase POST /api/geo/optimize
@router.post(
    "/geo/optimize",
    response_model=OptimizeResponse,
    summary="Alias for POST /api/optimize",
    description="Alias endpoint matching geo-map-phase specification.",
)
async def run_geo_optimization(req: OptimizeRequest) -> OptimizeResponse:
    return await run_optimization(req)


@router.get(
    "/blueprint",
    response_class=HTMLResponse,
    summary="Retrieve printable HTML engineering blueprint",
    description="Returns printable HTML blueprint for an optimization job.",
)
def get_blueprint(
    job_id: str = Query(..., description="Unique optimization job ID"),
) -> HTMLResponse:
    if job_id not in JOB_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blueprint for job_id '{job_id}' not found.",
        )

    job_data = JOB_STORE[job_id]
    html_content = job_data.get("blueprint_html", "")
    return HTMLResponse(content=html_content, status_code=200)

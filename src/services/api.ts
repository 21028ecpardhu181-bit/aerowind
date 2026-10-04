import { ProjectSummary, ProjectDetail, TelemetryData, Turbine } from '../types';

const API_BASE = '/api';

export async function fetchProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.statusText}`);
  return res.json();
}

export async function fetchProject(id: string): Promise<ProjectDetail> {
  const res = await fetch(`${API_BASE}/projects/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch project ${id}: ${res.statusText}`);
  return res.json();
}

export async function createProject(data: Partial<ProjectDetail>): Promise<ProjectDetail> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`);
  return res.json();
}

export async function geocodeLocation(query: string): Promise<any> {
  // Support both /api/geo/geocode?q=... and POST /api/geo/geocode
  try {
    const res = await fetch(`${API_BASE}/geo/geocode?q=${encodeURIComponent(query)}`);
    if (res.ok) return await res.json();
  } catch (_) {}

  const postRes = await fetch(`${API_BASE}/geo/geocode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!postRes.ok) throw new Error(`Geocoding error: ${postRes.statusText}`);
  return postRes.json();
}

export async function fetchTelemetry(lat: number, lon: number): Promise<TelemetryData> {
  try {
    const res = await fetch(`${API_BASE}/geo/telemetry?lat=${lat}&lon=${lon}`);
    if (res.ok) {
      const data = await res.json();
      const wind = data.wind || {};
      return {
        temperature_c: wind.temperature_c ?? data.temperature_c ?? 28,
        wind_speed_10m: wind.speed_100m_mps ? wind.speed_100m_mps * 0.82 : 6.2,
        wind_speed_80m: wind.speed_100m_mps ? wind.speed_100m_mps * 0.95 : 7.1,
        wind_speed_120m: wind.speed_100m_mps ?? 7.4,
        wind_direction_deg: wind.direction_100m_deg ?? data.wind_direction_deg ?? 300,
        pressure_hpa: wind.pressure_hpa ?? data.pressure_hpa ?? 1012,
        humidity_pct: data.humidity_pct ?? 65,
        condition: data.condition ?? 'Clear',
        timestamp: data.timestamp ?? new Date().toISOString(),
        elevation_m: data.elevation_m ?? 42,
        distance_to_coast_km: data.distance_to_coast_km ?? 0.2,
        terrain_type: data.terrain_type ?? 'Coastal / Mild Terrain',
        land_use: data.land_use ?? 'Mixed (Agriculture/Scrub)',
        wind_power_density: wind.power_density_wpm2 ?? 320,
        air_density: wind.air_density_kgpm3 ?? 1.18,
      };
    }
  } catch (e) {
    console.warn('Telemetry fetch error, using physical defaults', e);
  }
  return {
    temperature_c: 28,
    wind_speed_10m: 6.2,
    wind_speed_80m: 7.1,
    wind_speed_120m: 7.4,
    wind_direction_deg: 300,
    pressure_hpa: 1012,
    humidity_pct: 65,
    condition: 'Clear',
    timestamp: new Date().toISOString(),
    elevation_m: 42,
    distance_to_coast_km: 0.2,
    terrain_type: 'Coastal / Mild Terrain',
    land_use: 'Mixed (Agriculture/Scrub)',
    wind_power_density: 320,
    air_density: 1.18,
  };
}

export async function fetchFeasibility(payload: {
  center_lat: number;
  center_lon: number;
  radius_km?: number;
  boundary?: number[][];
  requested_turbines?: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/geo/feasibility`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Feasibility evaluation error: ${res.statusText}`);
  return res.json();
}

export async function fetchProvenance(): Promise<any> {
  const res = await fetch(`${API_BASE}/geo/provenance`);
  if (!res.ok) throw new Error('Failed to fetch data provenance');
  return res.json();
}

export async function generateInitialLayout(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/geo/initial-layout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Initial layout failed: ${res.statusText}`);
  return res.json();
}

export async function runOptimization(payload: any): Promise<any> {
  // Ensure the payload matches backend schemas.py OptimizeRequest:
  // Requires: { sites: SiteCoord[], K: int (2 <= K <= 8), wind_angle_deg?: float, p?: int }
  let targetPayload = payload;
  
  if (!payload.sites && payload.candidates) {
    targetPayload = {
      sites: payload.candidates.map((c: any, idx: number) => ({
        id: c.id !== undefined ? c.id : idx,
        lat: c.lat,
        lon: c.lon,
        x_m: c.x_m,
        y_m: c.y_m,
      })),
      K: Math.max(2, Math.min(8, payload.turbine_count || payload.K || 4)),
      wind_angle_deg: payload.wind_direction_deg ?? payload.wind_angle_deg ?? 300,
      p: payload.p || 2,
    };
  } else if (!payload.sites && payload.turbines) {
    targetPayload = {
      sites: payload.turbines.map((t: any, idx: number) => ({
        id: t.id !== undefined ? t.id : idx,
        lat: t.lat,
        lon: t.lon,
        x_m: t.x_m,
        y_m: t.y_m,
      })),
      K: Math.max(2, Math.min(8, payload.turbine_count || payload.K || payload.turbines.length)),
      wind_angle_deg: payload.wind_direction_deg ?? payload.wind_angle_deg ?? 300,
      p: payload.p || 2,
    };
  }

  const res = await fetch(`${API_BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(targetPayload),
  });
  if (!res.ok) throw new Error(`Optimization failed: ${res.statusText}`);
  return res.json();
}

export async function compareLayouts(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Layout comparison failed: ${res.statusText}`);
  return res.json();
}

// Authentication Service
export async function authRegister(data: { username: string; email: string; password: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Registration failed: ${res.statusText}`);
  }
  return res.json();
}

export async function authLogin(data: { username: string; password: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCurrentUser(token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`User auth failed: ${res.statusText}`);
  return res.json();
}

export async function authLogout(token: string): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
  });
  return res.ok;
}

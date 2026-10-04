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
  const res = await fetch(`${API_BASE}/geo/geocode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Geocoding error: ${res.statusText}`);
  return res.json();
}

export async function fetchTelemetry(lat: number, lon: number): Promise<TelemetryData> {
  try {
    const res = await fetch(`${API_BASE}/geo/telemetry?lat=${lat}&lon=${lon}`);
    if (res.ok) {
      const data = await res.json();
      return {
        temperature_c: data.temperature_c ?? 28,
        wind_speed_10m: data.wind_speed_10m ?? 6.2,
        wind_speed_80m: data.wind_speed_80m ?? 7.4,
        wind_speed_120m: data.wind_speed_120m ?? 7.8,
        wind_direction_deg: data.wind_direction_deg ?? 45,
        pressure_hpa: data.pressure_hpa ?? 1012,
        humidity_pct: data.humidity_pct ?? 65,
        condition: data.condition ?? 'Clear',
        timestamp: data.timestamp ?? new Date().toISOString(),
      };
    }
  } catch (e) {
    console.warn('Telemetry fetch error, using default live estimates', e);
  }
  return {
    temperature_c: 28,
    wind_speed_10m: 6.2,
    wind_speed_80m: 7.4,
    wind_speed_120m: 7.8,
    wind_direction_deg: 45,
    pressure_hpa: 1012,
    humidity_pct: 65,
    condition: 'Clear',
    timestamp: new Date().toISOString(),
  };
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
  const res = await fetch(`${API_BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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

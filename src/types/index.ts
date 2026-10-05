export type WorkflowScreen = 
  | 'home'
  | 'dashboard'
  | 's1_site'
  | 's2_config'
  | 's3_analysis'
  | 's4_optimize'
  | 's5_inspect'
  | 's6_blueprint';

export type ProjectStatus = 'draft' | 'configured' | 'analyzing' | 'simulated' | 'optimized' | 'blueprint_ready';

export interface ProjectSummary {
  id: string;
  name: string;
  location_name: string;
  latitude: number;
  longitude: number;
  area_km2?: number;
  turbine_count: number;
  turbine_model: string;
  suitability?: string;
  net_aep?: number;
  wake_loss_percent?: number;
  status: string;
  updated_at: string;
  thumbnail_url?: string;
}

export interface ProjectDetail extends ProjectSummary {
  rotor_diameter: number;
  hub_height: number;
  spacing_d: number;
  wind_speed: number;
  wind_direction: number;
  gross_aep?: number;
  turbines: Turbine[];
  boundary: number[][]; // [lat, lon][]
  created_at: string;
}

export interface Turbine {
  id: string;
  label?: string;
  displayLabel?: string;
  lat: number;
  lon: number;
  x_m?: number;
  y_m?: number;
  elevation_m?: number;
  effective_mps?: number;
  wake_deficit_pct?: number;
  power_kw?: number;
  is_conflicted?: boolean;
  conflict_desc?: string | null;
}

export interface SiteInfo {
  name: string;
  shortName: string;
  lat: number;
  lon: number;
  areaKm2: number;
  radiusKm?: number;
  perimeterKm?: number;
  elevationM: number;
  terrainType: string;
  distanceToCoastKm?: number;
  landUse?: string;
  windSpeedMps: number;
  windPowerDensity?: number;
  windDirectionDeg?: number;
  airDensityKgpm3?: number;
  pressureHpa?: number;
  temperatureC?: number;
  boundary?: number[][];
  feasibilityStats?: {
    count_preferred?: number;
    count_buildable?: number;
    count_excluded?: number;
    count_unknown?: number;
  };
}

export interface FarmConfig {
  turbineCount: number;
  model: string;
  modelName: string;
  rotorDiameter: number;
  hubHeight: number;
  ratedPowerKw: number;
  windDirectionDeg: number;
  spacingMultiplierD: number;
  wakeDecay: number;
  quboLambda: number;
  gridResolution: number;
}

export interface FeasibilityMask {
  preferred: number;
  buildable: number;
  restricted: number;
  excluded: number;
  unknown: number;
  reasons: string[];
}

export interface LayoutAnalysisData {
  turbines: Turbine[];
  candidates?: any[];
  candidate_positions?: any[];
  feasible_count?: number;
  requested_count?: number;
  gross_aep_gwh: number;
  net_aep_gwh: number;
  wake_loss_percent: number;
  min_spacing_m: number;
  conflicts_count: number;
  wake_conflicts_count?: number;
  wind_speed_mps: number;
  wind_direction_deg: number;
  wind_direction_label?: string;
  feasibility_mask?: FeasibilityMask;
  status_headline?: string;
  status_description?: string;
}

export interface OptimizationData {
  problem_name: string;
  variables_count: number;
  qubits_count: number;
  iterations_total: number;
  current_iteration: number;
  initial_aep_gwh: number;
  best_aep_gwh: number;
  initial_wake_loss_pct: number;
  best_wake_loss_pct: number;
  improvement_pct: number;
  turbine_count_target: number;
  turbine_count_actual: number;
  minimum_spacing_required_m: number;
  minimum_spacing_actual_m: number;
  optimized_turbines: Turbine[];
  status_headline: string;
  status_description: string;
  blueprint_url?: string;
  history?: Array<{
    iteration: number;
    aep: number;
    wake_loss: number;
    best_aep: number;
  }>;
}

export interface TelemetryData {
  temperature_c: number;
  wind_speed_10m: number;
  wind_speed_80m: number;
  wind_speed_120m: number;
  wind_direction_deg: number;
  pressure_hpa: number;
  humidity_pct: number;
  condition: string;
  timestamp: string;
  elevation_m?: number;
  distance_to_coast_km?: number;
  terrain_type?: string;
  land_use?: string;
  wind_power_density?: number;
  air_density?: number;
}

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  token?: string;
}

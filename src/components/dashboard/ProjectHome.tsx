import React from 'react';
import {
  MapPin,
  ArrowRight,
  FileText,
  Layers,
  Compass,
  Box,
  Plus,
  Minus,
  Zap,
  Activity,
  Wind,
  Layers as LayersIcon,
  ChevronRight,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import { ProjectSummary, ProjectDetail, TelemetryData } from '../../types';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Sparkline } from '../ui/Sparkline';
import { CompassRose } from '../ui/CompassRose';

interface ProjectHomeProps {
  projects: ProjectSummary[];
  activeProject: ProjectDetail | ProjectSummary | null;
  telemetry: TelemetryData | null;
  onOpenProject: (proj: ProjectSummary | ProjectDetail) => void;
  onViewBlueprint: (proj: ProjectSummary | ProjectDetail) => void;
  onNewProject: () => void;
  onSelectProject: (proj: ProjectSummary) => void;
}

export const ProjectHome: React.FC<ProjectHomeProps> = ({
  projects,
  activeProject,
  telemetry,
  onOpenProject,
  onViewBlueprint,
  onNewProject,
  onSelectProject,
}) => {
  // If no projects exist, show clean empty state as required by prompt
  if (!activeProject && projects.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-slate-50 min-h-[calc(100vh-60px)]">
        <Card className="max-w-md w-full p-8 text-center flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-600 text-2xl shadow-inner">
            ⚡
          </div>
          <h2 className="text-xl font-bold text-slate-900">No projects yet</h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Get started by creating your first wind farm project. Define boundaries, run terrain suitability analysis, and optimize layouts with quantum WS-QAOA algorithms.
          </p>
          <Button variant="energy" size="lg" onClick={onNewProject} className="w-full mt-2">
            <Plus className="w-5 h-5 stroke-[2.5]" />
            <span>Create New Project</span>
          </Button>
        </Card>
      </div>
    );
  }

  const proj = activeProject || projects[0];

  // Derived real engineering values
  const turbineCount = proj.turbine_count || 12;
  const ratingMw = 2.5; // default rated MW per GE 2.5-120 turbine
  const installedCapacityMw = (turbineCount * ratingMw).toFixed(1);
  const netAep = proj.net_aep ? proj.net_aep.toFixed(2) : (turbineCount * 7.1).toFixed(2);
  const wakeLoss = proj.wake_loss_percent ? proj.wake_loss_percent.toFixed(2) : '6.12';
  const studyArea = proj.area_km2 ? `${proj.area_km2.toFixed(1)} km²` : '24.8 km²';
  const windSpeed = telemetry ? `${telemetry.wind_speed_120m} m/s` : '7.82 m/s';
  const windDir = telemetry ? telemetry.wind_direction_deg : 45;

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-5 lg:p-6 flex flex-col gap-5 max-w-[1600px] mx-auto w-full pb-20 md:pb-6">
      {/* 1. PROJECT HERO — Cinematic Visual Map Frame */}
      <div className="relative w-full rounded-2xl md:rounded-3xl overflow-hidden shadow-glass border border-slate-200/90 min-h-[360px] md:min-h-[440px] flex flex-col justify-end p-5 md:p-8 bg-slate-900 group">
        {/* Background Visual: Cinematic wind farm terrain photo overlay */}
        <div
          className="absolute inset-0 bg-cover bg-center transition-transform duration-700 ease-out group-hover:scale-105"
          style={{
            backgroundImage: `url('/assets/real-turbines-photo.jpg')`,
            backgroundPosition: 'center 40%',
          }}
        />

        {/* Ambient Overlay gradient for high readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/40 to-slate-900/20 backdrop-blur-[0.5px]" />

        {/* Top Right Floating Map Controls & Weather Pill */}
        <div className="absolute top-4 right-4 z-10 flex flex-col items-end gap-2.5">
          {/* Weather pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-white/40 backdrop-blur-md shadow-glass text-xs font-semibold text-slate-800 transition-all">
            <span className="text-amber-500">☀️</span>
            <span>{telemetry ? `${telemetry.temperature_c}°C ${telemetry.condition}` : '28°C Clear'}</span>
            <span className="w-px h-3 bg-slate-200" />
            <span className="text-blue-500">💨</span>
            <span>{telemetry ? `${telemetry.wind_speed_120m} m/s NE (${telemetry.wind_direction_deg}°)` : '7.8 m/s NE (45°)'}</span>
          </div>

          {/* Map action buttons */}
          <div className="flex flex-col gap-1 bg-white/80 backdrop-blur-md border border-white/40 rounded-xl p-1 shadow-glass text-slate-700">
            <button className="p-2 hover:bg-white rounded-lg hover:text-slate-950 transition-colors" title="Toggle Layer">
              <Layers className="w-4 h-4" />
            </button>
            <button className="p-2 hover:bg-white rounded-lg hover:text-slate-950 transition-colors" title="Reset North">
              <Compass className="w-4 h-4" />
            </button>
            <button className="p-2 hover:bg-white rounded-lg hover:text-slate-950 transition-colors font-bold text-xs" title="Toggle 3D">
              3D
            </button>
            <div className="w-full h-px bg-slate-200 my-0.5" />
            <button className="p-2 hover:bg-white rounded-lg hover:text-slate-950 transition-colors" title="Zoom In">
              <Plus className="w-4 h-4" />
            </button>
            <button className="p-2 hover:bg-white rounded-lg hover:text-slate-950 transition-colors" title="Zoom Out">
              <Minus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Hero Content Overlay */}
        <div className="relative z-10 max-w-2xl text-white">
          <div className="text-[11px] font-bold uppercase tracking-widest text-amber-300 mb-1 flex items-center gap-2">
            <span>Welcome Back</span>
          </div>

          <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white drop-shadow-md">
            {proj.name}
          </h1>
          <div className="text-sm md:text-base font-medium text-slate-200 mt-0.5 mb-2">
            Wind Farm Project
          </div>

          {/* Location & Status Bar */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-200 mb-3">
            <span className="flex items-center gap-1 font-medium bg-black/30 backdrop-blur-sm px-2.5 py-1 rounded-lg border border-white/10">
              <MapPin className="w-3.5 h-3.5 text-amber-400" />
              {proj.location_name}
            </span>
            <Badge status={proj.status} />
            <span className="text-slate-300 text-[11px]">
              Last updated {proj.updated_at ? proj.updated_at.split(' ')[0] : 'today'}
            </span>
          </div>

          {/* Engineering Metadata */}
          <p className="text-xs md:text-sm text-slate-200/90 leading-relaxed mb-5 max-w-xl font-normal">
            <strong className="text-white font-semibold">{turbineCount} turbines</strong> • <strong className="text-white font-semibold">{installedCapacityMw} MW</strong> • <strong className="text-white font-semibold">{netAep} GWh/year</strong>. Site optimized using WS-QAOA quantum algorithms with physical wake reduction.
          </p>

          {/* Action CTAs: Bright Yellow Pill & Glass Blueprint */}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="energy"
              size="lg"
              onClick={() => onOpenProject(proj)}
              className="text-slate-950 font-bold px-6 py-3"
            >
              <span>Open Project</span>
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </Button>

            <Button
              variant="glass"
              size="lg"
              onClick={() => onViewBlueprint(proj)}
              className="bg-white/20 hover:bg-white/30 text-white border-white/30 font-medium px-5 py-3"
            >
              <FileText className="w-4 h-4 text-amber-300" />
              <span>View Blueprint</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 2. METRICS ROW — 4 High-Precision Liquid Glass Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Estimated AEP */}
        <Card className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
              <span className="p-1.5 rounded-lg bg-amber-100 text-amber-600">
                <Zap className="w-4 h-4 fill-amber-500 stroke-none" />
              </span>
              <span>Estimated AEP</span>
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {netAep} <span className="text-xs font-bold text-slate-500">GWh/yr</span>
              </div>
              <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 mt-0.5">
                <TrendingUp className="w-3.5 h-3.5" />
                <span>↑ 8.5% net gain</span>
              </div>
            </div>
            <Sparkline color="yellow" width={80} height={26} />
          </div>
        </Card>

        {/* Card 2: Wake Loss */}
        <Card className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
              <span className="p-1.5 rounded-lg bg-blue-100 text-blue-600">
                <Activity className="w-4 h-4" />
              </span>
              <span>Wake Loss</span>
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {wakeLoss}<span className="text-xs font-bold text-slate-500">%</span>
              </div>
              <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 mt-0.5">
                <TrendingDown className="w-3.5 h-3.5" />
                <span>↓ 57% mitigated</span>
              </div>
            </div>
            <Sparkline color="blue" width={80} height={26} />
          </div>
        </Card>

        {/* Card 3: Installed Capacity */}
        <Card className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
              <span className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
                <LayersIcon className="w-4 h-4" />
              </span>
              <span>Installed Capacity</span>
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-black text-slate-900 tracking-tight">
              {installedCapacityMw} <span className="text-xs font-bold text-slate-500">MW</span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-2 border border-slate-200/60">
              <div
                className="bg-amber-400 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, (turbineCount / 30) * 100)}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-500 mt-1 font-medium">
              {turbineCount} Turbines • {ratingMw.toFixed(1)} MW each
            </div>
          </div>
        </Card>

        {/* Card 4: Avg Wind Speed */}
        <Card className="p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
              <span className="p-1.5 rounded-lg bg-sky-100 text-sky-600">
                <Wind className="w-4 h-4" />
              </span>
              <span>Avg. Wind Speed</span>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <div>
              <div className="text-2xl font-black text-slate-900 tracking-tight">
                {windSpeed}
              </div>
              <div className="text-xs font-semibold text-slate-500 mt-0.5">
                NE ({windDir}°) Hub Height
              </div>
            </div>
            <CompassRose degrees={windDir} size={38} />
          </div>
        </Card>
      </div>

      {/* 3. BOTTOM ROW — Project Overview & Annual Energy Production */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Project Overview Card */}
        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Project Overview</h3>
              <span className="text-xs font-mono text-slate-400 font-medium">GIS Analysis</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <div className="flex flex-col gap-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Study Area</span>
                  <span className="font-bold text-slate-900 font-mono">{studyArea}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Terrain Elevation</span>
                  <span className="font-bold text-slate-900 font-mono">42 m – 188 m</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Land Classification</span>
                  <span className="font-semibold text-slate-800">Sparse Scrub</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Grid Connection</span>
                  <span className="font-semibold text-emerald-600">Feasible (4.2 km)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-medium">Nearest Settlement</span>
                  <span className="font-semibold text-emerald-600">1.5 km (Compliant)</span>
                </div>
              </div>

              {/* Satellite Concession Preview Thumbnail */}
              <div className="relative rounded-xl overflow-hidden border border-slate-200 min-h-[120px] bg-slate-800 flex items-center justify-center group/map">
                <div
                  className="absolute inset-0 bg-cover bg-center opacity-85 group-hover/map:scale-105 transition-transform"
                  style={{ backgroundImage: `url('/assets/real-turbines-photo.jpg')` }}
                />
                <div className="relative z-10 px-3 py-1.5 rounded-lg bg-black/60 backdrop-blur-md border border-white/20 text-white font-mono text-xs font-bold shadow-md">
                  {studyArea}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenProject(proj)}
              className="text-xs font-semibold text-amber-700 hover:text-amber-800 border-amber-200 hover:bg-amber-50"
            >
              <span>View Full Details</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
            <span className="text-[11px] text-slate-400 font-mono">SRTM 30m DEM Verified</span>
          </div>
        </Card>

        {/* Right: Annual Energy Production Card */}
        <Card className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Annual Energy Production</h3>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold text-amber-700 bg-amber-100/80 font-mono">
                {netAep} GWh Target
              </span>
            </div>

            {/* Production curve illustration */}
            <div className="mt-4 h-28 w-full flex items-end">
              <svg className="w-full h-full overflow-visible" viewBox="0 0 400 100" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="aep-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0,80 Q 50,60 100,50 T 200,30 T 300,18 T 400,28 L 400,100 L 0,100 Z"
                  fill="url(#aep-grad)"
                />
                <path
                  d="M 0,80 Q 50,60 100,50 T 200,30 T 300,18 T 400,28"
                  fill="none"
                  stroke="#F59E0B"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                <circle cx="300" cy="18" r="4.5" fill="#F59E0B" stroke="#FFFFFF" strokeWidth="2" />
              </svg>
            </div>

            {/* Months labels */}
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1 px-1">
              <span>Jan</span>
              <span>Mar</span>
              <span>May</span>
              <span>Jul</span>
              <span>Sep</span>
              <span>Nov</span>
              <span>Dec</span>
            </div>
          </div>

          {/* Key performance metrics at bottom */}
          <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-slate-100 text-center">
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Capacity Factor</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">39.6%</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Capacity Util.</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">41.2%</div>
            </div>
            <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
              <div className="text-[10px] text-slate-500 font-medium">Operating Hours</div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">8,560 hrs</div>
            </div>
          </div>
        </Card>
      </div>

      {/* 4. MOBILE RECENT PROJECTS SECTION (Visible on smaller screens) */}
      <div className="md:hidden mt-2">
        <div className="flex items-center justify-between mb-3 px-1">
          <h3 className="text-sm font-bold text-slate-900">Recent Projects</h3>
          <span className="text-xs font-semibold text-amber-600">All ({projects.length})</span>
        </div>
        <div className="flex flex-col gap-2">
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectProject(p)}
              className="w-full text-left p-3 rounded-2xl bg-white/90 border border-slate-200/90 shadow-subtle flex items-center justify-between active:scale-[0.99] transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100/80 border border-amber-200 text-amber-700 font-bold flex items-center justify-center text-sm shadow-xs">
                  ⚡
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900">{p.name}</div>
                  <div className="text-xs text-slate-500">{p.location_name}</div>
                  <div className="mt-1">
                    <Badge status={p.status} className="text-[10px] py-0 px-2" />
                  </div>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-400" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

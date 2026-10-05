import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Clock,
  Cloud,
  Compass,
  Cpu,
  Crosshair,
  ChevronRight,
  FileText,
  Gauge,
  Leaf,
  Map,
  MoreHorizontal,
  Mountain,
  Plus,
  Search,
  Thermometer,
  Wind,
  Zap,
} from 'lucide-react';
import { ProjectSummary, ProjectDetail, TelemetryData, WorkflowScreen } from '../../types';

interface CreateNewProjectHeroProps {
  onNewProject: () => void;
  onSearchLocation?: (query: string) => void;
  onNavigateTo?: (screen: WorkflowScreen) => void;
  projects?: ProjectSummary[];
  activeProject?: ProjectSummary | ProjectDetail | null;
  telemetry?: TelemetryData | null;
  onSelectProject?: (p: ProjectSummary) => void;
}

export const CreateNewProjectHero: React.FC<CreateNewProjectHeroProps> = ({
  onNewProject,
  onSearchLocation,
  onNavigateTo,
  projects = [],
  activeProject,
  telemetry,
  onSelectProject,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Benchmark / active project matching the reference image
  const displayProject: ProjectSummary = (activeProject as ProjectSummary) || (projects.length > 0 ? projects[0] : {
    id: 'proj-bommuru-01',
    name: 'Bommuru Wind Farm',
    location_name: 'Andhra Pradesh, India',
    latitude: 17.0005,
    longitude: 81.7800,
    area_km2: 24.8,
    turbine_count: 12,
    turbine_model: 'GE 2.5-120',
    suitability: 'Preferred',
    net_aep: 88.3,
    wake_loss_percent: 3.5,
    status: 'Optimized',
    updated_at: 'Just now',
  });

  // Real backend metrics (matching reference image telemetry)
  const windSpeed = (telemetry?.wind_speed_120m !== undefined && telemetry?.wind_speed_120m > 0
    ? telemetry.wind_speed_120m
    : 8.4).toFixed(1);
  const elevation = telemetry?.elevation_m !== undefined && telemetry?.elevation_m > 0
    ? telemetry.elevation_m
    : 42;
  const netAep = (displayProject.net_aep || 88.3).toFixed(1);
  const wakeLoss = (displayProject.wake_loss_percent || 3.5).toFixed(1);

  const handleSearchSubmit = () => {
    const q = searchQuery.trim();
    if (q && onSearchLocation) {
      onSearchLocation(q);
    } else if (q) {
      onNewProject();
    }
  };

  const handleUseGPS = () => {
    if (navigator.geolocation && onSearchLocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          onSearchLocation(`${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
        },
        () => {
          if (onSearchLocation) onSearchLocation('Bommuru, Andhra Pradesh');
        }
      );
    } else if (onSearchLocation) {
      onSearchLocation('Bommuru, Andhra Pradesh');
    }
  };

  return (
    <div className="flex-1 relative min-h-[calc(100vh-64px)] flex flex-col justify-start overflow-x-hidden selection:bg-[#FFD21F] selection:text-slate-950">
      
      {/* ────────────────────────────────────────────────────────── */}
      {/* ── 1. BACKGROUND IMAGES (Mobile vs Desktop)             ── */}
      {/* ────────────────────────────────────────────────────────── */}
      {/* Mobile Background: Pristine Sunrise Landscape */}
      <div
        className="block md:hidden absolute inset-0 bg-cover bg-[position:center_top] pointer-events-none transition-transform duration-1000 ease-out"
        style={{
          backgroundImage: `url('/assets/hero-windfarm-generated.jpg')`,
          backgroundRepeat: 'no-repeat',
        }}
      />
      <div className="block md:hidden absolute inset-0 bg-gradient-to-b from-white/10 via-transparent to-[#F8FAFC] pointer-events-none" />

      {/* Desktop Background: High-Res Turbine Cutaway with Bright Sky */}
      <div
        className="hidden md:block absolute inset-0 bg-cover bg-[position:center_18%] pointer-events-none transition-transform duration-1000 ease-out"
        style={{
          backgroundImage: `url('/assets/desktop-turbine-cutaway.jpg')`,
          backgroundRepeat: 'no-repeat',
        }}
      />
      <div className="hidden md:block absolute inset-0 bg-gradient-to-b from-sky-200/10 via-transparent to-slate-900/15 pointer-events-none" />


      {/* ────────────────────────────────────────────────────────── */}
      {/* ── 2. MOBILE VIEW: PRESERVED 100% AS-IS (md:hidden)     ── */}
      {/* ────────────────────────────────────────────────────────── */}
      <div className="block md:hidden relative z-10 w-full max-w-md mx-auto px-4 pt-2.5 pb-36 flex flex-col gap-3">
        {/* Eyebrow Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/80 backdrop-blur-xl border border-white/90 shadow-[0_2px_8px_rgba(0,0,0,0.04),inset_0_1px_1px_rgba(255,255,255,0.95)] w-fit select-none">
          <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" />
          <span className="text-[10px] font-black tracking-widest text-slate-800 uppercase">
            CLEAN ENERGY FUTURE
          </span>
        </div>

        {/* Large Concise Headline */}
        <h1 className="text-4xl sm:text-5xl font-black text-slate-950 leading-[1.05] tracking-tight">
          Design <br />
          <span className="text-[#F59E0B] drop-shadow-xs">Smarter</span> <br />
          Wind Farms
        </h1>

        {/* Short Supporting Text */}
        <p className="text-xs sm:text-sm text-slate-700 font-semibold leading-relaxed max-w-[310px]">
          Real terrain. Real data. Quantum-optimized micro-siting for a cleaner, greener planet.
        </p>

        {/* Real Project Metrics (4 Compact Liquid Glass Cards) */}
        <div className="grid grid-cols-4 gap-2 mt-1">
          {/* Metric 1: Avg Wind Speed */}
          <div className="bg-white/60 hover:bg-white/80 backdrop-blur-xl border border-white/80 rounded-2xl p-2 sm:p-2.5 shadow-[0_8px_20px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col items-start transition-all">
            <div className="w-7 h-7 rounded-full bg-amber-500/15 text-amber-700 flex items-center justify-center mb-1.5 shadow-xs">
              <Wind className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
            <div className="text-xs sm:text-sm font-black text-slate-950 leading-tight">
              {windSpeed} <span className="text-[9px] text-slate-600 font-bold">m/s</span>
            </div>
            <div className="text-[8.5px] sm:text-[9.5px] text-slate-500 font-medium leading-tight mt-0.5 truncate w-full">
              Avg Wind Speed
            </div>
          </div>

          {/* Metric 2: Elevation */}
          <div className="bg-white/60 hover:bg-white/80 backdrop-blur-xl border border-white/80 rounded-2xl p-2 sm:p-2.5 shadow-[0_8px_20px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col items-start transition-all">
            <div className="w-7 h-7 rounded-full bg-orange-500/15 text-orange-700 flex items-center justify-center mb-1.5 shadow-xs">
              <Mountain className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
            <div className="text-xs sm:text-sm font-black text-slate-950 leading-tight">
              {elevation} <span className="text-[9px] text-slate-600 font-bold">m</span>
            </div>
            <div className="text-[8.5px] sm:text-[9.5px] text-slate-500 font-medium leading-tight mt-0.5 truncate w-full">
              Elevation
            </div>
          </div>

          {/* Metric 3: Est. Net AEP */}
          <div className="bg-white/60 hover:bg-white/80 backdrop-blur-xl border border-white/80 rounded-2xl p-2 sm:p-2.5 shadow-[0_8px_20px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col items-start transition-all">
            <div className="w-7 h-7 rounded-full bg-yellow-500/20 text-yellow-700 flex items-center justify-center mb-1.5 shadow-xs">
              <Zap className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
            <div className="text-xs sm:text-sm font-black text-slate-950 leading-tight">
              {netAep} <span className="text-[9px] text-slate-600 font-bold">GWh</span>
            </div>
            <div className="text-[8.5px] sm:text-[9.5px] text-slate-500 font-medium leading-tight mt-0.5 truncate w-full">
              Est. Net AEP
            </div>
          </div>

          {/* Metric 4: Wake Loss */}
          <div className="bg-white/60 hover:bg-white/80 backdrop-blur-xl border border-white/80 rounded-2xl p-2 sm:p-2.5 shadow-[0_8px_20px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col items-start transition-all">
            <div className="w-7 h-7 rounded-full bg-emerald-500/15 text-emerald-700 flex items-center justify-center mb-1.5 shadow-xs">
              <Leaf className="w-3.5 h-3.5 stroke-[2.5]" />
            </div>
            <div className="text-xs sm:text-sm font-black text-slate-950 leading-tight">
              {wakeLoss} <span className="text-[9px] text-slate-600 font-bold">%</span>
            </div>
            <div className="text-[8.5px] sm:text-[9.5px] text-slate-500 font-medium leading-tight mt-0.5 truncate w-full">
              Wake Loss
            </div>
          </div>
        </div>

        {/* Main Action Card: Search + Create Button */}
        <div className="bg-white/75 hover:bg-white/85 backdrop-blur-2xl border border-white/90 rounded-[28px] p-3 sm:p-3.5 shadow-[0_16px_40px_rgba(0,0,0,0.08),inset_0_1px_2px_rgba(255,255,255,0.95)] flex flex-col gap-2.5 mt-1 transition-all">
          <div className="flex items-center gap-2 bg-white/95 border border-slate-200/80 rounded-full px-3.5 py-2.5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)] focus-within:border-amber-400 focus-within:ring-2 focus-within:ring-amber-400/20 transition-all">
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              id="input-homepage-search"
              type="text"
              placeholder="Search location, village or coordinates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearchSubmit();
              }}
              className="flex-1 bg-transparent text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 font-medium focus:outline-none"
            />
            <button
              id="btn-homepage-gps"
              type="button"
              onClick={handleUseGPS}
              className="w-7 h-7 rounded-full bg-slate-50 hover:bg-slate-100 active:scale-95 border border-slate-200 flex items-center justify-center text-slate-600 hover:text-amber-600 transition-colors shrink-0 cursor-pointer"
              title="Use current GPS location"
            >
              <Crosshair className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            id="btn-project-new"
            onClick={onNewProject}
            className="w-full bg-[#FFD21F] hover:bg-[#F2C50F] active:scale-[0.98] text-slate-950 font-black text-sm py-3.5 px-5 rounded-full flex items-center justify-between shadow-[0_8px_24px_rgba(255,210,31,0.45),inset_0_1px_1px_rgba(255,255,255,0.9)] transition-all cursor-pointer"
          >
            <Plus className="w-5 h-5 stroke-[3]" />
            <span className="font-black tracking-tight text-sm sm:text-base">Create New Project</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>

        {/* Workflow: 4 Compact Visual Cards */}
        <div className="grid grid-cols-4 gap-2 mt-1">
          <div
            id="card-workflow-site"
            onClick={() => (onNavigateTo ? onNavigateTo('s1_site') : onNewProject())}
            className="bg-white/65 hover:bg-white/85 active:scale-98 backdrop-blur-xl border border-white/85 rounded-2xl p-2.5 flex flex-col justify-between min-h-[135px] shadow-[0_8px_24px_rgba(0,0,0,0.04),inset_0_1px_1px_rgba(255,255,255,0.95)] cursor-pointer group transition-all"
          >
            <div>
              <div className="w-7 h-7 rounded-xl bg-amber-500/20 text-amber-700 flex items-center justify-center mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Map className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-xs font-black text-slate-950 leading-tight">Select Site</h3>
              <p className="text-[9px] text-slate-500 font-medium leading-tight mt-0.5">Real GIS & Terrain Analysis</p>
            </div>
            <div className="w-6 h-6 rounded-full bg-white/95 border border-slate-200/60 shadow-xs flex items-center justify-center text-slate-700 group-hover:bg-[#FFD21F] group-hover:text-slate-950 group-hover:border-transparent transition-all self-end mt-2">
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>

          <div
            id="card-workflow-config"
            onClick={() => onNavigateTo?.('s2_config')}
            className="bg-white/65 hover:bg-white/85 active:scale-98 backdrop-blur-xl border border-white/85 rounded-2xl p-2.5 flex flex-col justify-between min-h-[135px] shadow-[0_8px_24px_rgba(0,0,0,0.04),inset_0_1px_1px_rgba(255,255,255,0.95)] cursor-pointer group transition-all"
          >
            <div>
              <div className="w-7 h-7 rounded-xl bg-orange-500/20 text-orange-700 flex items-center justify-center mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Wind className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-xs font-black text-slate-950 leading-tight">Configure Farm</h3>
              <p className="text-[9px] text-slate-500 font-medium leading-tight mt-0.5">Turbines & Constraints</p>
            </div>
            <div className="w-6 h-6 rounded-full bg-white/95 border border-slate-200/60 shadow-xs flex items-center justify-center text-slate-700 group-hover:bg-[#FFD21F] group-hover:text-slate-950 group-hover:border-transparent transition-all self-end mt-2">
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>

          <div
            id="card-workflow-optimize"
            onClick={() => onNavigateTo?.('s4_optimize')}
            className="bg-white/65 hover:bg-white/85 active:scale-98 backdrop-blur-xl border border-white/85 rounded-2xl p-2.5 flex flex-col justify-between min-h-[135px] shadow-[0_8px_24px_rgba(0,0,0,0.04),inset_0_1px_1px_rgba(255,255,255,0.95)] cursor-pointer group transition-all"
          >
            <div>
              <div className="w-7 h-7 rounded-xl bg-amber-600/20 text-amber-800 flex items-center justify-center mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Cpu className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-xs font-black text-slate-950 leading-tight">Quantum Optimize</h3>
              <p className="text-[9px] text-slate-500 font-medium leading-tight mt-0.5">WS-QAOA Micro-siting</p>
            </div>
            <div className="w-6 h-6 rounded-full bg-white/95 border border-slate-200/60 shadow-xs flex items-center justify-center text-slate-700 group-hover:bg-[#FFD21F] group-hover:text-slate-950 group-hover:border-transparent transition-all self-end mt-2">
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>

          <div
            id="card-workflow-blueprint"
            onClick={() => onNavigateTo?.('s6_blueprint')}
            className="bg-white/65 hover:bg-white/85 active:scale-98 backdrop-blur-xl border border-white/85 rounded-2xl p-2.5 flex flex-col justify-between min-h-[135px] shadow-[0_8px_24px_rgba(0,0,0,0.04),inset_0_1px_1px_rgba(255,255,255,0.95)] cursor-pointer group transition-all"
          >
            <div>
              <div className="w-7 h-7 rounded-xl bg-amber-700/20 text-amber-900 flex items-center justify-center mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <FileText className="w-4 h-4 stroke-[2.2]" />
              </div>
              <h3 className="text-xs font-black text-slate-950 leading-tight">View Blueprint</h3>
              <p className="text-[9px] text-slate-500 font-medium leading-tight mt-0.5">Coordinates & Export</p>
            </div>
            <div className="w-6 h-6 rounded-full bg-white/95 border border-slate-200/60 shadow-xs flex items-center justify-center text-slate-700 group-hover:bg-[#FFD21F] group-hover:text-slate-950 group-hover:border-transparent transition-all self-end mt-2">
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>
        </div>

        {/* Recent Projects Card */}
        <div className="bg-white/80 hover:bg-white/90 backdrop-blur-2xl border border-white/90 rounded-[28px] p-3.5 shadow-[0_8px_30px_rgba(0,0,0,0.06),inset_0_1px_2px_rgba(255,255,255,0.95)] flex flex-col gap-2.5 mt-1 transition-all">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-1.5 text-xs font-black text-slate-950">
              <Clock className="w-3.5 h-3.5 text-slate-600" />
              <span>Recent Projects</span>
            </div>
            <button
              id="btn-recent-projects-view-all"
              onClick={() => onNavigateTo?.('dashboard')}
              className="text-[11px] font-bold text-slate-600 hover:text-slate-950 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div
            id="card-recent-project-item"
            onClick={() => {
              if (onSelectProject) {
                onSelectProject(displayProject);
              } else if (onNavigateTo) {
                onNavigateTo('dashboard');
              }
            }}
            className="bg-white/90 hover:bg-white border border-slate-200/70 rounded-2xl p-2.5 shadow-[0_2px_8px_rgba(0,0,0,0.03)] flex items-center justify-between gap-3 cursor-pointer group transition-all active:scale-[0.99]"
          >
            <div className="flex items-center gap-3 min-w-0">
              <img
                src="/assets/windfarm-explore-thumb.jpg"
                alt={displayProject.name}
                className="w-14 h-14 rounded-xl object-cover shrink-0 border border-slate-200/80 shadow-xs"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = '/assets/real-turbines-photo.jpg';
                }}
              />
              <div className="flex flex-col min-w-0">
                <h3 className="text-xs sm:text-sm font-black text-slate-950 group-hover:text-amber-600 transition-colors truncate">
                  {displayProject.name}
                </h3>
                <p className="text-[10px] sm:text-xs text-slate-500 font-medium truncate mt-0.5">
                  {displayProject.location_name}
                </p>
                <div className="flex items-center gap-2.5 mt-1.5 text-[10px] font-semibold text-slate-600">
                  <span className="flex items-center gap-1">
                    <Wind className="w-3 h-3 text-slate-400" />
                    <span>{displayProject.turbine_count || 12} Turbines</span>
                  </span>
                  <span className="flex items-center gap-1 text-amber-700">
                    <Zap className="w-3 h-3 text-amber-500 fill-amber-500" />
                    <span>{(displayProject.net_aep || 88.3).toFixed(1)} GWh/yr</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <BarChart3 className="w-3 h-3 text-slate-400" />
                    <span>{(displayProject.wake_loss_percent || 3.5).toFixed(1)}%</span>
                  </span>
                </div>
              </div>
            </div>
            <div className="w-7 h-7 rounded-full bg-slate-100/90 flex items-center justify-center text-slate-400 group-hover:bg-[#FFD21F] group-hover:text-slate-950 transition-all shrink-0">
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      </div>


      {/* ────────────────────────────────────────────────────────── */}
      {/* ── 3. DESKTOP VIEW: APPLE LIQUID GLASS (hidden md:flex)  ── */}
      {/* ────────────────────────────────────────────────────────── */}
      <div className="hidden md:flex flex-col relative z-10 w-full min-h-[calc(100vh-64px)] p-6 lg:p-8 justify-between gap-6 max-w-[1520px] mx-auto">
        
        {/* Desktop Top Toolbar: Location Search & Workflow Shortcuts & CTA */}
        <div className="w-full flex items-center justify-between gap-4 bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-2xl px-4 py-2.5 shadow-[0_8px_30px_rgba(0,0,0,0.05),inset_0_1px_1px_rgba(255,255,255,0.9)] transition-all">
          {/* Location Search Bar with GPS */}
          <div className="flex items-center gap-2 bg-white/95 border border-slate-200/80 rounded-xl px-3 py-1.5 w-72 lg:w-84 focus-within:border-amber-400 focus-within:ring-2 focus-within:ring-amber-400/20 transition-all shadow-xs">
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              id="input-homepage-search"
              type="text"
              placeholder="Search site, village, coords..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearchSubmit();
              }}
              className="bg-transparent text-xs text-slate-900 placeholder:text-slate-400 font-medium focus:outline-none w-full"
            />
            <button
              id="btn-homepage-gps"
              type="button"
              onClick={handleUseGPS}
              className="w-6 h-6 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-amber-600 flex items-center justify-center transition-colors cursor-pointer"
              title="Use GPS"
            >
              <Crosshair className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Workflow Shortcuts */}
          <div className="flex items-center gap-2">
            <button
              id="card-workflow-site"
              onClick={() => (onNavigateTo ? onNavigateTo('s1_site') : onNewProject())}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-slate-200/60 text-xs font-bold text-slate-800 shadow-xs hover:border-amber-300 transition-all cursor-pointer"
            >
              <Map className="w-3.5 h-3.5 text-amber-600" />
              <span>Select Site</span>
            </button>
            <button
              id="card-workflow-config"
              onClick={() => onNavigateTo?.('s2_config')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-slate-200/60 text-xs font-bold text-slate-800 shadow-xs hover:border-amber-300 transition-all cursor-pointer"
            >
              <Wind className="w-3.5 h-3.5 text-orange-600" />
              <span>Configure Farm</span>
            </button>
            <button
              id="card-workflow-optimize"
              onClick={() => onNavigateTo?.('s4_optimize')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-slate-200/60 text-xs font-bold text-slate-800 shadow-xs hover:border-amber-300 transition-all cursor-pointer"
            >
              <Cpu className="w-3.5 h-3.5 text-amber-700" />
              <span>Quantum Optimize</span>
            </button>
            <button
              id="card-workflow-blueprint"
              onClick={() => onNavigateTo?.('s6_blueprint')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-slate-200/60 text-xs font-bold text-slate-800 shadow-xs hover:border-amber-300 transition-all cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5 text-amber-800" />
              <span>Blueprint</span>
            </button>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5">
            <button
              id="btn-recent-projects-view-all"
              onClick={() => onNavigateTo?.('dashboard')}
              className="px-3.5 py-1.5 rounded-xl bg-white/80 hover:bg-white border border-slate-200/70 text-xs font-bold text-slate-700 shadow-xs transition-all cursor-pointer"
            >
              Recent Projects ({projects.length})
            </button>
            <button
              id="btn-project-new"
              onClick={onNewProject}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#FFD21F] hover:bg-[#F2C50F] active:scale-98 text-slate-950 font-black text-xs shadow-[0_4px_16px_rgba(255,210,31,0.4)] transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Create New Project</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Upper Section: Performance Trends on left, Center clear view of turbine, Wind Turbine #2 Callout on right */}
        <div className="w-full grid grid-cols-12 gap-6 items-start my-auto">
          {/* Left: Performance Trends Card */}
          <div className="col-span-12 lg:col-span-4 xl:col-span-3 bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-5 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] transition-all">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-black text-slate-950 tracking-tight">Performance Trends</h3>
              <span className="text-[10px] font-bold text-slate-400">QAOA vs Wake</span>
            </div>
            <div className="relative mt-2">
              <div className="flex">
                {/* Y-axis labels */}
                <div className="flex flex-col justify-between text-[9px] font-bold text-slate-400 pr-2 h-24 select-none">
                  <span>1.0</span>
                  <span>1.0</span>
                  <span>1.0</span>
                  <span>1.0</span>
                  <span>1.0</span>
                </div>
                {/* SVG Waves */}
                <svg viewBox="0 0 260 100" className="w-full h-24 overflow-visible">
                  {/* Guideline */}
                  <line x1="140" y1="5" x2="140" y2="95" stroke="#E2E8F0" strokeDasharray="3 3" strokeWidth="1.5" />
                  {/* Wave 1: Dark Slate */}
                  <path
                    d="M 10 75 C 35 45, 60 40, 85 60 C 110 80, 125 90, 140 65 C 160 40, 185 15, 210 35 C 230 50, 245 70, 255 60"
                    fill="none"
                    stroke="#0F172A"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Wave 2: Golden Yellow */}
                  <path
                    d="M 10 50 C 35 30, 60 35, 90 60 C 115 85, 130 90, 140 80 C 160 55, 185 10, 210 25 C 230 40, 245 50, 255 45"
                    fill="none"
                    stroke="#F59E0B"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Highlight points on guideline */}
                  <circle cx="140" cy="65" r="3.5" fill="#0F172A" stroke="#FFFFFF" strokeWidth="2" />
                  <circle cx="140" cy="80" r="3.5" fill="#F59E0B" stroke="#FFFFFF" strokeWidth="2" />
                </svg>
              </div>
              {/* X-axis ticks */}
              <div className="flex items-center justify-between text-[9px] font-bold text-slate-400 pl-6 mt-1 select-none">
                {[0, 1, 2, 3, 4, 5, 6, 7].map((num) => (
                  <span key={num}>{num}</span>
                ))}
                <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-900 flex items-center justify-center text-[8.5px] font-black">
                  8
                </span>
                {[9, 10, 11, 12, 13].map((num) => (
                  <span key={num}>{num}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Middle Spacer: Leaves photorealistic turbine nacelle & copper coils clearly visible */}
          <div className="hidden lg:block lg:col-span-4 xl:col-span-5 pointer-events-none" />

          {/* Right: Floating Wind Turbine #2 Callout Card (Pinned near generator cutaway) */}
          <div className="col-span-12 lg:col-span-4 xl:col-span-4 flex justify-end">
            <div className="w-full max-w-sm bg-white/75 hover:bg-white/85 backdrop-blur-2xl border border-white/90 rounded-[28px] p-5 shadow-[0_16px_40px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.95)] transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_#f59e0b]" />
                  <h3 className="text-xs font-black text-slate-950">Wind Turbine #2</h3>
                </div>
                <button className="text-slate-400 hover:text-slate-700 text-xs font-bold transition-colors">✕</button>
              </div>
              <div className="flex flex-col gap-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-semibold text-[11px]">Status</span>
                  <span className="px-2.5 py-0.5 rounded-lg bg-[#FFD21F] text-slate-950 font-black text-[10px]">Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-semibold text-[11px]">Rotor</span>
                  <span className="text-slate-900 font-bold">0</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-semibold text-[11px]">Nacelle</span>
                  <span className="text-slate-900 font-bold">Aligned</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-semibold text-[11px]">Converter</span>
                  <span className="text-slate-900 font-bold">Running</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500 font-semibold text-[11px]">Alarms</span>
                  <span className="px-2 py-0.5 rounded bg-white border border-slate-200/80 font-bold text-slate-900 text-[10px]">0</span>
                </div>
                <div className="w-full bg-[#FFD21F] text-slate-950 font-black text-xs py-2 px-3 rounded-xl flex items-center justify-between mt-1 shadow-xs">
                  <span>Warnings</span>
                  <span className="font-black">2</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Section: 4 Apple Liquid Glass Metric Cards */}
        <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-auto">
          {/* Card 1: Real-Time Power */}
          <div className="bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-5 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col justify-between gap-3 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-black text-slate-950">Real-Time Power</h3>
              </div>
              <MoreHorizontal className="w-4 h-4 text-slate-400" />
            </div>

            {/* Circular Arc Gauge */}
            <div className="relative flex flex-col items-center justify-center my-1">
              <svg viewBox="0 0 180 110" className="w-44 h-28 overflow-visible">
                {/* Background Track (220 degree arc) */}
                <path
                  d="M 30 90 A 60 60 0 1 1 150 90"
                  fill="none"
                  stroke="#E2E8F0"
                  strokeWidth="8"
                  strokeLinecap="round"
                />
                {/* Active Power Arc in Energy Yellow */}
                <path
                  d="M 30 90 A 60 60 0 0 1 115 32"
                  fill="none"
                  stroke="#FFD21F"
                  strokeWidth="8"
                  strokeLinecap="round"
                />
                {/* Ticks & Labels */}
                <text x="24" y="105" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">200</text>
                <text x="32" y="45" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">400</text>
                <text x="90" y="24" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">600</text>
                <text x="148" y="45" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">800</text>
                <text x="160" y="75" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">1000</text>
                <text x="156" y="105" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">1200</text>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pt-5">
                <span className="text-2xl font-black text-slate-950 tracking-tight leading-none">417 kW</span>
                <span className="text-[10px] font-bold text-slate-500 mt-1">43.8%</span>
              </div>
            </div>

            {/* 4 Metrics Matrix */}
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Capacity Range</span>
                <span className="font-bold text-slate-900 mt-0.5">0 – 1.4 MW</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Average Output</span>
                <span className="font-bold text-slate-900 mt-0.5">336.7 kW</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Gauge Value</span>
                <span className="font-bold text-slate-900 mt-0.5">402 kW</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Capacity %</span>
                <span className="font-bold text-slate-900 mt-0.5">41.2%</span>
              </div>
            </div>
          </div>

          {/* Card 2: Weather Forecast & Temperature */}
          <div className="flex flex-col gap-3">
            {/* Weather Forecast */}
            <div className="bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-4 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] transition-all">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <Cloud className="w-3.5 h-3.5 text-slate-700" />
                  <h3 className="text-xs font-black text-slate-950">Weather Forecast</h3>
                </div>
                <MoreHorizontal className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <div className="grid grid-cols-4 gap-1.5 text-center">
                <div className="bg-[#FFD21F] rounded-2xl p-2 shadow-xs flex flex-col items-center">
                  <span className="text-[10px] font-black text-slate-950">Now</span>
                  <span className="text-xs font-black text-slate-950 mt-1">{telemetry?.temperature_c || 27}°C</span>
                  <span className="text-[9.5px] font-bold text-slate-900 mt-0.5">{windSpeed} m/s</span>
                </div>
                <div className="bg-white/70 border border-slate-200/60 rounded-2xl p-2 flex flex-col items-center">
                  <span className="text-[10px] font-semibold text-slate-500">2:00 PM</span>
                  <span className="text-xs font-bold text-slate-900 mt-1">30°C</span>
                  <span className="text-[9.5px] font-medium text-slate-600 mt-0.5">6.9 m/s</span>
                </div>
                <div className="bg-white/70 border border-slate-200/60 rounded-2xl p-2 flex flex-col items-center">
                  <span className="text-[10px] font-semibold text-slate-500">3:00 PM</span>
                  <span className="text-xs font-bold text-slate-900 mt-1">32°C</span>
                  <span className="text-[9.5px] font-medium text-slate-600 mt-0.5">7.3 m/s</span>
                </div>
                <div className="bg-white/70 border border-slate-200/60 rounded-2xl p-2 flex flex-col items-center">
                  <span className="text-[10px] font-semibold text-slate-500">4:00 PM</span>
                  <span className="text-xs font-bold text-slate-900 mt-1">29°C</span>
                  <span className="text-[9.5px] font-medium text-slate-600 mt-0.5">5.6 m/s</span>
                </div>
              </div>
            </div>

            {/* Temperature */}
            <div className="bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-4 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] transition-all">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <Thermometer className="w-3.5 h-3.5 text-slate-700" />
                  <h3 className="text-xs font-black text-slate-950">Temperature</h3>
                </div>
                <MoreHorizontal className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <div className="grid grid-cols-4 gap-2 text-center text-xs font-bold text-slate-900 mb-1.5">
                <span>74°C</span>
                <span>28°C</span>
                <span>79°C</span>
                <span>35°C</span>
              </div>
              <div className="grid grid-cols-4 gap-2 h-12 items-end">
                <div className="h-full w-full bg-slate-100/90 rounded-lg flex flex-col justify-end p-0.5 overflow-hidden">
                  <div className="w-full h-[74%] bg-gradient-to-t from-amber-400 to-[#FFD21F] rounded-md shadow-xs" />
                </div>
                <div className="h-full w-full bg-slate-100/90 rounded-lg flex flex-col justify-end p-0.5 overflow-hidden relative">
                  <div className="w-full h-[32%] bg-gradient-to-t from-amber-400 to-[#FFD21F] rounded-md flex items-center justify-center shadow-xs">
                    <AlertTriangle className="w-3 h-3 text-amber-900" />
                  </div>
                </div>
                <div className="h-full w-full bg-slate-100/90 rounded-lg flex flex-col justify-end p-0.5 overflow-hidden">
                  <div className="w-full h-[79%] bg-gradient-to-t from-amber-400 to-[#FFD21F] rounded-md shadow-xs" />
                </div>
                <div className="h-full w-full bg-slate-100/90 rounded-lg flex flex-col justify-end p-0.5 overflow-hidden">
                  <div className="w-full h-[38%] bg-gradient-to-t from-amber-400 to-[#FFD21F] rounded-md shadow-xs" />
                </div>
              </div>
              <div className="grid grid-cols-4 gap-2 text-center text-[9.5px] font-semibold text-slate-500 mt-1.5">
                <span>Bearing</span>
                <span>Ambient</span>
                <span>Rotor</span>
                <span>Stator</span>
              </div>
            </div>
          </div>

          {/* Card 3: Wind Direction */}
          <div className="bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-5 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col justify-between gap-3 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-black text-slate-950">Wind Direction</h3>
              </div>
              <MoreHorizontal className="w-4 h-4 text-slate-400" />
            </div>

            {/* Compass Rose */}
            <div className="flex items-center justify-center my-1">
              <svg viewBox="0 0 150 150" className="w-32 h-32 overflow-visible">
                <circle cx="75" cy="75" r="58" fill="none" stroke="#E2E8F0" strokeWidth="1.5" />
                <circle cx="75" cy="75" r="48" fill="none" stroke="#CBD5E1" strokeWidth="1" strokeDasharray="2 3" />
                <text x="75" y="12" textAnchor="middle" className="text-[9px] fill-slate-600 font-black">0°</text>
                <text x="140" y="78" textAnchor="middle" className="text-[9px] fill-slate-600 font-black">90°</text>
                <text x="75" y="145" textAnchor="middle" className="text-[9px] fill-slate-600 font-black">180°</text>
                <text x="10" y="78" textAnchor="middle" className="text-[9px] fill-slate-600 font-black">270°</text>
                <g transform="rotate(128, 75, 75)">
                  <polygon points="75,22 80,70 75,75" fill="#FFD21F" />
                  <polygon points="75,22 70,70 75,75" fill="#F59E0B" />
                  <polygon points="75,128 80,80 75,75" fill="#E2E8F0" />
                  <polygon points="75,128 70,80 75,75" fill="#CBD5E1" />
                  <polygon points="128,75 80,70 75,75" fill="#FFD21F" />
                  <polygon points="128,75 80,80 75,75" fill="#F59E0B" />
                  <polygon points="22,75 70,70 75,75" fill="#E2E8F0" />
                  <polygon points="22,75 70,80 75,75" fill="#CBD5E1" />
                  <circle cx="75" cy="75" r="7" fill="#0F172A" stroke="#FFFFFF" strokeWidth="2" />
                  <circle cx="75" cy="75" r="2.5" fill="#FFD21F" />
                </g>
              </svg>
            </div>

            {/* 6 Metrics Grid (3 cols x 2 rows) */}
            <div className="grid grid-cols-3 gap-1.5 text-[9.5px]">
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Current</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">128° (SE)</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Avg</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">121°</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Min/Max</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">109°/142°</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Rotor Speed</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">13.6°</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Wind Speed</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">{windSpeed} m/s</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-1.5 flex flex-col">
                <span className="text-slate-400 font-medium">Active Power</span>
                <span className="font-bold text-slate-900 mt-0.5 truncate">368 kW</span>
              </div>
            </div>
          </div>

          {/* Card 4: System Overview */}
          <div className="bg-white/70 hover:bg-white/80 backdrop-blur-2xl border border-white/90 rounded-[28px] p-5 shadow-[0_12px_36px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex flex-col justify-between gap-3 transition-all">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Gauge className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-black text-slate-950">System Overview</h3>
              </div>
              <MoreHorizontal className="w-4 h-4 text-slate-400" />
            </div>

            {/* Speedometer Radial Gauge */}
            <div className="relative flex flex-col items-center justify-center my-1">
              <svg viewBox="0 0 180 110" className="w-44 h-28 overflow-visible">
                <path
                  d="M 25 90 A 65 65 0 1 1 155 90"
                  fill="none"
                  stroke="#E2E8F0"
                  strokeWidth="1.5"
                  strokeDasharray="2 4"
                />
                <text x="30" y="105" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">0</text>
                <text x="25" y="65" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">40</text>
                <text x="50" y="30" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">60</text>
                <text x="90" y="18" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">80</text>
                <text x="130" y="30" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">100</text>
                <text x="155" y="65" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">120</text>
                <text x="150" y="105" textAnchor="middle" className="text-[8px] fill-slate-400 font-bold">140</text>
                <line x1="45" y1="45" x2="52" y2="40" stroke="#FFD21F" strokeWidth="4" strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pt-5">
                <span className="text-3xl font-black text-slate-950 tracking-tight leading-none">57</span>
                <span className="text-[10px] font-bold text-slate-500 mt-1 uppercase tracking-wider">MWh</span>
              </div>
            </div>

            {/* 4 Metrics Matrix */}
            <div className="grid grid-cols-2 gap-2 text-[10px]">
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Power</span>
                <span className="font-bold text-slate-900 mt-0.5">57 MWh</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Rotor RPM</span>
                <span className="font-bold text-slate-900 mt-0.5">19.4 RPM</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Capacity Utilization</span>
                <span className="font-bold text-slate-900 mt-0.5">39.6%</span>
              </div>
              <div className="bg-white/80 border border-slate-200/60 rounded-xl p-2 flex flex-col">
                <span className="text-slate-400 font-medium truncate">Operational Hours</span>
                <span className="font-bold text-slate-900 mt-0.5">14,860 hrs</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

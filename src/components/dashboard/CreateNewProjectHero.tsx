import React from 'react';
import {
  ArrowRight,
  FileText,
  Layers,
  Wind,
  Plus,
  Play,
  BarChart2,
  ShieldCheck,
  CheckCircle2,
  Zap,
  Globe2
} from 'lucide-react';
import { AeroQuantumLogo } from '../ui/AeroQuantumLogo';

interface CreateNewProjectHeroProps {
  onNewProject: () => void;
}

export const CreateNewProjectHero: React.FC<CreateNewProjectHeroProps> = ({
  onNewProject,
}) => {
  return (
    <div className="flex-1 relative min-h-[calc(100vh-60px)] pb-48 md:pb-24 flex flex-col justify-start overflow-x-hidden selection:bg-[#FFD21F] selection:text-slate-950">
      {/* ── 1. PHOTOREALISTIC WIND FARM SUNRISE BACKGROUND ── */}
      <div
        className="absolute inset-0 bg-cover bg-[position:center_top] pointer-events-none transition-transform duration-1000 ease-out"
        style={{
          backgroundImage: `url('/assets/hero-windfarm-generated.jpg')`,
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Subtle cinematic gradient: preserves 100% photo visibility while giving perfect contrast for text */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/15 via-transparent to-slate-950/25 pointer-events-none" />

      {/* ── 2. MAIN LIQUID GLASS CONTAINER ── */}
      <div className="relative z-10 w-full max-w-4xl mx-auto px-4 sm:px-6 pt-3 sm:pt-6 flex flex-col gap-4 sm:gap-6">
        
        {/* Top Hero Row: Eyebrow + Headline on left, Floating Metric Card on right */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pt-2 sm:pt-4">
          {/* Left Headline */}
          <div className="flex flex-col max-w-sm sm:max-w-md">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/40 hover:bg-white/50 backdrop-blur-xl border border-white/60 shadow-[0_2px_8px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.8)] w-fit mb-2 transition-all select-none">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_6px_#10b981]" />
              <span className="text-[10px] sm:text-[11px] font-black tracking-[0.2em] text-slate-900 uppercase">
                SUSTAINABLE ENERGY
              </span>
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-slate-950 leading-[1.08] tracking-tight drop-shadow-[0_1px_2px_rgba(255,255,255,0.8)]">
              Optimizing <br />
              <span className="bg-gradient-to-r from-amber-600 via-amber-500 to-[#FFD21F] bg-clip-text text-transparent drop-shadow-xs">
                Wind Energy
              </span> <br />
              for a Cleaner Planet
            </h1>
            <p className="text-xs sm:text-sm font-bold text-slate-900 mt-2 sm:mt-3 leading-relaxed max-w-[280px] sm:max-w-sm drop-shadow-[0_1px_1px_rgba(255,255,255,0.8)]">
              Powered by real satellite terrain cadastre, Open-Meteo telemetry, and quantum WS-QAOA micro-siting.
            </p>
          </div>

          {/* Right: Floating Apple Liquid Glass Metric Card */}
          <div className="self-end sm:self-auto mt-2 sm:mt-4 backdrop-blur-2xl bg-white/25 hover:bg-white/35 border border-white/50 rounded-2xl p-3 sm:p-4 shadow-[0_16px_40px_rgba(0,0,0,0.12),inset_0_1px_1px_rgba(255,255,255,0.8)] max-w-[170px] sm:max-w-[200px] transition-all select-none">
            <div className="flex items-center gap-1.5 mb-2">
              <div className="w-5 h-5 rounded-lg bg-slate-950 text-white flex items-center justify-center p-1 shadow-xs">
                <BarChart2 className="w-3 h-3 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-black text-slate-950 leading-tight">
                Advanced Optimization
              </span>
            </div>
            <div className="w-8 h-0.5 bg-[#FFD21F] rounded-full mb-2" />
            <ul className="text-[10px] sm:text-[11px] text-slate-950 font-bold space-y-1">
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_4px_#f59e0b]" />
                <span>Higher Net AEP</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_4px_#f59e0b]" />
                <span>Lower Wake Loss</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_4px_#f59e0b]" />
                <span>Guaranteed Boundary</span>
              </li>
            </ul>
          </div>
        </div>

        {/* ── 3. MAIN ACTION CARD: APPLE LIQUID GLASS ── */}
        <div className="backdrop-blur-3xl bg-white/25 hover:bg-white/35 border border-white/50 rounded-3xl p-4 sm:p-6 shadow-[0_20px_60px_rgba(0,0,0,0.15),inset_0_1px_2px_rgba(255,255,255,0.85)] transition-all">
          {/* Header: Interactive Logo on left, Yellow Create Button on right */}
          <div className="flex items-center justify-between gap-3">
            <div 
              className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-white/40 hover:bg-white/60 active:scale-95 border border-white/60 flex items-center justify-center shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),0_4px_12px_rgba(0,0,0,0.06)] cursor-pointer group transition-all"
              title="Interactive AeroQuantum Turbine - Tap to spin blades"
            >
              <AeroQuantumLogo size={42} interactive={true} />
            </div>
            <button
              id="btn-project-new"
              onClick={onNewProject}
              className="bg-[#FFD21F] hover:bg-[#F2C50F] active:scale-95 text-slate-950 font-black text-xs sm:text-sm px-4 sm:px-6 py-2.5 sm:py-3 rounded-full flex items-center gap-2 shadow-[0_8px_24px_rgba(255,210,31,0.5),inset_0_1px_1px_rgba(255,255,255,0.8)] transition-all cursor-pointer shrink-0"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Create New Project</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </button>
          </div>

          {/* Title & Description */}
          <div className="mt-3 sm:mt-4">
            <h2 className="text-base sm:text-xl font-black text-slate-950 tracking-tight drop-shadow-[0_1px_0_rgba(255,255,255,0.6)]">
              Start a New Wind Farm Project
            </h2>
            <p className="text-[11px] sm:text-sm text-slate-900 font-semibold leading-relaxed mt-1 drop-shadow-[0_1px_0_rgba(255,255,255,0.5)]">
              Select or search any village in India to automatically load its official cadastral boundary, evaluate Copernicus DEM terrain & ISRIC soil bearing physics, and optimize micro-siting layouts using quantum WS-QAOA.
            </p>
          </div>

          {/* 3-Column Stepped Pipeline */}
          <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-3.5 sm:mt-5 pt-3 sm:pt-4 border-t border-white/40">
            {/* Step 1: Select Site */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl bg-white/20 hover:bg-white/40 active:scale-98 backdrop-blur-xl transition-all cursor-pointer group border border-white/40 hover:border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)]"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-800 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-110 transition-transform">
                <Layers className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-black text-slate-950">1. Select Site</span>
              <span className="text-[9px] sm:text-[10px] text-slate-800 font-bold leading-tight mt-0.5">
                Auto-load village cadastre & terrain
              </span>
            </div>

            {/* Step 2: Farm Configuration */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl bg-white/20 hover:bg-white/40 active:scale-98 backdrop-blur-xl transition-all cursor-pointer group border border-white/40 hover:border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)]"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-800 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-110 transition-transform">
                <Wind className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-black text-slate-950">2. Configure Farm</span>
              <span className="text-[9px] sm:text-[10px] text-slate-800 font-bold leading-tight mt-0.5">
                Set turbine count, model & spacing
              </span>
            </div>

            {/* Step 3: Quantum WS-QAOA */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl bg-white/20 hover:bg-white/40 active:scale-98 backdrop-blur-xl transition-all cursor-pointer group border border-white/40 hover:border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)]"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-800 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-110 transition-transform">
                <FileText className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-black text-slate-950">3. Quantum QAOA</span>
              <span className="text-[9px] sm:text-[10px] text-slate-800 font-bold leading-tight mt-0.5">
                Optimize micro-siting & get blueprint
              </span>
            </div>
          </div>
        </div>

        {/* ── 4. EXPLORER / DEMO LIQUID GLASS CARD ── */}
        <div
          onClick={onNewProject}
          className="backdrop-blur-3xl bg-white/20 hover:bg-white/30 border border-white/45 rounded-2xl p-2.5 sm:p-3.5 shadow-[0_12px_36px_rgba(0,0,0,0.1),inset_0_1px_1px_rgba(255,255,255,0.7)] flex items-center justify-between gap-3 cursor-pointer active:scale-[0.99] transition-all group select-none"
        >
          <div className="flex items-center gap-3">
            <div className="relative w-20 sm:w-24 h-12 sm:h-14 rounded-xl overflow-hidden shrink-0 border border-white/70 shadow-xs group-hover:scale-105 transition-transform duration-300">
              <img
                src="/assets/windfarm-explore-thumb.jpg"
                alt="Explore wind farm demo preview"
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = '/assets/real-turbines-photo.jpg';
                }}
              />
              <div className="absolute inset-0 bg-black/25 flex items-center justify-center">
                <div className="w-6 h-6 rounded-full bg-white/95 text-slate-950 flex items-center justify-center shadow-md">
                  <Play className="w-3 h-3 fill-slate-950 ml-0.5" />
                </div>
              </div>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider text-amber-800">
                <Globe2 className="w-3 h-3 text-amber-600" />
                <span>EXPLORE WORKFLOW</span>
              </div>
              <h3 className="text-xs sm:text-sm font-black text-slate-950">
                Live Geotechnical & Quantum Siting Pipeline
              </h3>
              <p className="text-[10px] sm:text-xs text-slate-800 font-bold leading-tight line-clamp-1">
                From satellite cadastral boundaries to Jensen wake minimization in minutes.
              </p>
            </div>
          </div>
          <div className="w-8 h-8 rounded-full border border-white/70 bg-white/50 hover:bg-white/70 flex items-center justify-center text-slate-900 group-hover:border-amber-400 group-hover:text-amber-600 shrink-0 transition-colors shadow-xs">
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
};

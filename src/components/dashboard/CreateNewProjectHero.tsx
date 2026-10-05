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
    <div className="flex-1 relative min-h-[calc(100vh-60px)] pb-36 md:pb-16 flex flex-col justify-start overflow-x-hidden selection:bg-[#FFD21F] selection:text-slate-950">
      {/* ── 1. PHOTOREALISTIC WIND FARM SUNRISE BACKGROUND ── */}
      <div
        className="absolute inset-0 bg-cover bg-top sm:bg-center pointer-events-none transition-transform duration-1000 ease-out"
        style={{
          backgroundImage: `url('/assets/hero-windfarm-generated.jpg')`,
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Gentle liquid glow gradients: keeps photo fully visible while maximizing text legibility */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/20 via-white/35 to-slate-100/85 pointer-events-none" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-gradient-to-tr from-amber-400/20 via-yellow-300/15 to-transparent blur-3xl rounded-full pointer-events-none" />

      {/* ── 2. MAIN LIQUID GLASS CONTAINER ── */}
      <div className="relative z-10 w-full max-w-4xl mx-auto px-4 sm:px-6 pt-3 sm:pt-6 flex flex-col gap-4 sm:gap-6">
        
        {/* Top Hero Row: Eyebrow + Headline on left, Floating Metric Card on right */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pt-2 sm:pt-4">
          {/* Left Headline */}
          <div className="flex flex-col max-w-sm sm:max-w-md">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/70 backdrop-blur-md border border-white/80 shadow-xs w-fit mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] sm:text-[11px] font-black tracking-[0.2em] text-slate-800 uppercase">
                SUSTAINABLE ENERGY
              </span>
            </div>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-slate-950 leading-[1.08] tracking-tight drop-shadow-xs">
              Optimizing <br />
              <span className="bg-gradient-to-r from-amber-600 via-amber-500 to-[#FFD21F] bg-clip-text text-transparent">
                Wind Energy
              </span> <br />
              for a Cleaner Planet
            </h1>
            <p className="text-xs sm:text-sm font-semibold text-slate-700 mt-2 sm:mt-3 leading-relaxed max-w-[280px] sm:max-w-sm">
              Powered by real satellite terrain cadastre, Open-Meteo telemetry, and quantum WS-QAOA micro-siting.
            </p>
          </div>

          {/* Right: Floating Apple Liquid Glass Metric Card */}
          <div className="self-end sm:self-auto mt-2 sm:mt-4 backdrop-blur-3xl bg-white/60 hover:bg-white/75 border border-white/85 rounded-2xl p-3 sm:p-4 shadow-[0_16px_40px_rgba(15,23,42,0.12),inset_0_1px_2px_rgba(255,255,255,0.9)] max-w-[170px] sm:max-w-[200px] transition-all select-none">
            <div className="flex items-center gap-1.5 mb-2">
              <div className="w-5 h-5 rounded-lg bg-slate-950 text-white flex items-center justify-center p-1 shadow-xs">
                <BarChart2 className="w-3 h-3 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-950 leading-tight">
                Advanced Optimization
              </span>
            </div>
            <div className="w-8 h-0.5 bg-[#FFD21F] rounded-full mb-2" />
            <ul className="text-[10px] sm:text-[11px] text-slate-800 font-semibold space-y-1">
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-amber-500" />
                <span>Higher Net AEP</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-amber-500" />
                <span>Lower Wake Loss</span>
              </li>
              <li className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-amber-500" />
                <span>Guaranteed Boundary</span>
              </li>
            </ul>
          </div>
        </div>

        {/* ── 3. MAIN ACTION CARD: APPLE LIQUID GLASS ── */}
        <div className="backdrop-blur-3xl bg-white/65 hover:bg-white/80 border border-white/90 rounded-3xl p-4 sm:p-6 shadow-[0_20px_60px_rgba(15,23,42,0.12),inset_0_1px_3px_rgba(255,255,255,0.95)] transition-all">
          {/* Header: Logo on left, Yellow Create Button on right */}
          <div className="flex items-center justify-between gap-3">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-white/80 border border-white flex items-center justify-center shadow-sm">
              <AeroQuantumLogo size={42} />
            </div>
            <button
              id="btn-project-new"
              onClick={onNewProject}
              className="bg-[#FFD21F] hover:bg-[#F2C50F] active:scale-95 text-slate-950 font-black text-xs sm:text-sm px-4 sm:px-6 py-2.5 sm:py-3 rounded-full flex items-center gap-2 shadow-[0_8px_24px_rgba(255,210,31,0.45),inset_0_1px_1px_rgba(255,255,255,0.8)] transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Create New Project</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </button>
          </div>

          {/* Title & Description */}
          <div className="mt-3 sm:mt-4">
            <h2 className="text-base sm:text-xl font-black text-slate-950 tracking-tight">
              Start a New Wind Farm Project
            </h2>
            <p className="text-[11px] sm:text-sm text-slate-600 font-normal leading-relaxed mt-1">
              Select or search any village in India to automatically load its official cadastral boundary, evaluate Copernicus DEM terrain & ISRIC soil bearing physics, and optimize micro-siting layouts using quantum WS-QAOA.
            </p>
          </div>

          {/* 3-Column Stepped Pipeline */}
          <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-3.5 sm:mt-5 pt-3 sm:pt-4 border-t border-slate-200/60">
            {/* Step 1: Select Site */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl hover:bg-white/70 backdrop-blur-md transition-all cursor-pointer group border border-transparent hover:border-white/80 shadow-none hover:shadow-sm"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-700 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Layers className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">1. Select Site</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Auto-load village cadastre & terrain
              </span>
            </div>

            {/* Step 2: Farm Configuration */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl hover:bg-white/70 backdrop-blur-md transition-all border-l border-slate-200/60 pl-2.5 sm:pl-3 cursor-pointer group border-t border-r border-b border-transparent hover:border-white/80 shadow-none hover:shadow-sm"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-700 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Wind className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">2. Configure Farm</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Set turbine count, model & spacing
              </span>
            </div>

            {/* Step 3: Quantum WS-QAOA */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-2 sm:p-2.5 rounded-2xl hover:bg-white/70 backdrop-blur-md transition-all border-l border-slate-200/60 pl-2.5 sm:pl-3 cursor-pointer group border-t border-r border-b border-transparent hover:border-white/80 shadow-none hover:shadow-sm"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-700 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <FileText className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">3. Quantum QAOA</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Optimize micro-siting & get blueprint
              </span>
            </div>
          </div>
        </div>

        {/* ── 4. EXPLORER / DEMO LIQUID GLASS CARD ── */}
        <div
          onClick={onNewProject}
          className="backdrop-blur-3xl bg-white/60 hover:bg-white/80 border border-white/85 rounded-2xl p-2.5 sm:p-3.5 shadow-[0_12px_36px_rgba(15,23,42,0.1),inset_0_1px_2px_rgba(255,255,255,0.9)] flex items-center justify-between gap-3 cursor-pointer active:scale-[0.99] transition-all group select-none"
        >
          <div className="flex items-center gap-3">
            <div className="relative w-20 sm:w-24 h-12 sm:h-14 rounded-xl overflow-hidden shrink-0 border border-white/80 shadow-xs group-hover:scale-105 transition-transform duration-300">
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
              <div className="flex items-center gap-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">
                <Globe2 className="w-3 h-3 text-amber-600" />
                <span>EXPLORE WORKFLOW</span>
              </div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-950">
                Live Geotechnical & Quantum Siting Pipeline
              </h3>
              <p className="text-[10px] sm:text-xs text-slate-600 leading-tight line-clamp-1">
                From satellite cadastral boundaries to Jensen wake minimization in minutes.
              </p>
            </div>
          </div>
          <div className="w-8 h-8 rounded-full border border-white/90 bg-white/80 flex items-center justify-center text-slate-700 group-hover:border-amber-400 group-hover:text-amber-600 shrink-0 transition-colors shadow-xs">
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
};

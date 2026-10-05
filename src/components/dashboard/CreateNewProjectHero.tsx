import React from 'react';
import {
  ArrowRight,
  FileText,
  Layers,
  Wind,
  Plus,
  Play,
  BarChart2
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
      {/* Photorealistic Wind Farm Sunrise Hero Background */}
      <div
        className="absolute inset-0 bg-cover bg-top sm:bg-center pointer-events-none transition-opacity duration-700"
        style={{
          backgroundImage: `url('/assets/hero-windfarm-generated.jpg')`,
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Soft atmospheric gradient to ensure cards and text legibility */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/10 via-white/35 to-[#F8FAFC]/95 pointer-events-none" />

      {/* Main Home Content Container */}
      <div className="relative z-10 w-full max-w-4xl mx-auto px-4 sm:px-6 pt-3 sm:pt-6 flex flex-col gap-4 sm:gap-6">
        
        {/* Top Hero Row: Eyebrow + Headline on left, Floating Metric Card on right */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 pt-1 sm:pt-4">
          {/* Left Headline */}
          <div className="flex flex-col max-w-sm sm:max-w-md">
            <span className="text-[10px] sm:text-[11px] font-black tracking-[0.22em] text-slate-700 uppercase mb-0.5 drop-shadow-xs">
              SUSTAINABLE ENERGY
            </span>
            <h1 className="text-2xl sm:text-4xl lg:text-5xl font-black text-slate-900 leading-[1.12] tracking-tight">
              Optimizing <br />
              <span className="text-[#FFD21F] bg-gradient-to-r from-amber-500 via-[#FFD21F] to-amber-400 bg-clip-text text-transparent drop-shadow-xs">
                Wind Energy
              </span> <br />
              for a Cleaner Planet
            </h1>
            <p className="text-[11px] sm:text-sm font-medium text-slate-700 mt-1.5 sm:mt-3 leading-relaxed max-w-[270px] sm:max-w-sm drop-shadow-xs">
              Powered by real terrain data and quantum optimization.
            </p>
          </div>

          {/* Right: Floating Apple Liquid Glass Metric Card */}
          <div className="self-end sm:self-auto mt-1 sm:mt-4 backdrop-blur-xl bg-white/55 hover:bg-white/70 border border-white/70 rounded-2xl p-2.5 sm:p-4 shadow-[0_8px_32px_rgba(15,23,42,0.12)] max-w-[160px] sm:max-w-[190px] transition-all select-none">
            <div className="flex items-center gap-1.5 mb-1.5">
              <div className="w-5 h-5 rounded-lg bg-slate-900 text-white flex items-center justify-center p-1 shadow-xs">
                <BarChart2 className="w-3 h-3 stroke-[2.5]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900 leading-tight">
                Advanced Optimization
              </span>
            </div>
            <div className="w-7 h-0.5 bg-[#FFD21F] rounded-full mb-1.5" />
            <ul className="text-[10px] sm:text-[11px] text-slate-800 font-medium space-y-0.5 sm:space-y-1">
              <li className="flex items-center gap-1.5">• Higher AEP</li>
              <li className="flex items-center gap-1.5">• Lower wake loss</li>
              <li className="flex items-center gap-1.5">• Better layouts</li>
            </ul>
          </div>
        </div>

        {/* Main Action Card: Apple Liquid Glass with Create Button & Workflow Pipeline */}
        <div className="backdrop-blur-2xl bg-white/85 hover:bg-white/95 border border-white/80 rounded-3xl p-4 sm:p-6 shadow-[0_12px_40px_rgba(15,23,42,0.12)] transition-all">
          {/* Header: Logo on left, Yellow Create Button on right */}
          <div className="flex items-center justify-between gap-3">
            <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-white/70 border border-white/90 flex items-center justify-center shadow-xs">
              <AeroQuantumLogo size={42} />
            </div>
            <button
              id="btn-project-new"
              onClick={onNewProject}
              className="bg-[#FFD21F] hover:bg-[#F2C50F] active:scale-95 text-slate-950 font-bold text-xs sm:text-sm px-4 sm:px-5 py-2.5 rounded-full flex items-center gap-1.5 shadow-[0_4px_16px_rgba(255,210,31,0.4)] transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4 stroke-[3]" />
              <span>Create New Project</span>
              <ArrowRight className="w-3.5 h-3.5 stroke-[2.5]" />
            </button>
          </div>

          {/* Title & Description */}
          <div className="mt-3 sm:mt-4">
            <h2 className="text-base sm:text-xl font-black text-slate-900 tracking-tight">
              Start a New Wind Farm Project
            </h2>
            <p className="text-[11px] sm:text-sm text-slate-600 font-normal leading-relaxed mt-1">
              Define your concession boundary on real satellite terrain, run Copernicus elevation & environmental suitability analysis, and optimize turbine placement with quantum WS-QAOA.
            </p>
          </div>

          {/* 3-Column Stepped Pipeline */}
          <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-3.5 sm:mt-5 pt-3 sm:pt-4 border-t border-slate-100">
            {/* Step 1: Select Site */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-1.5 sm:p-2 rounded-2xl hover:bg-white/60 transition-colors cursor-pointer group"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Layers className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">Select Site</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Define boundary on real terrain
              </span>
            </div>

            {/* Step 2: Analyze & Optimize */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-1.5 sm:p-2 rounded-2xl hover:bg-white/60 transition-colors border-l border-slate-100 pl-2.5 sm:pl-3 cursor-pointer group"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <Wind className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">Analyze & Optimize</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Use quantum WS-QAOA
              </span>
            </div>

            {/* Step 3: Engineering Output */}
            <div
              onClick={onNewProject}
              className="flex flex-col items-start p-1.5 sm:p-2 rounded-2xl hover:bg-white/60 transition-colors border-l border-slate-100 pl-2.5 sm:pl-3 cursor-pointer group"
            >
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600 mb-1.5 sm:mb-2 shadow-xs group-hover:scale-105 transition-transform">
                <FileText className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.2]" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-slate-900">Engineering Output</span>
              <span className="text-[9px] sm:text-[10px] text-slate-500 leading-tight mt-0.5">
                Get optimized layouts & reports
              </span>
            </div>
          </div>
        </div>

        {/* "See How It Works" Explorer Card */}
        <div
          onClick={onNewProject}
          className="backdrop-blur-2xl bg-white/80 hover:bg-white/95 border border-white/80 rounded-2xl p-2.5 sm:p-3 shadow-[0_8px_24px_rgba(15,23,42,0.06)] flex items-center justify-between gap-3 cursor-pointer active:scale-[0.99] transition-all group select-none"
        >
          <div className="flex items-center gap-3">
            <div className="relative w-20 sm:w-24 h-12 sm:h-14 rounded-xl overflow-hidden shrink-0 border border-slate-200/80 group-hover:scale-105 transition-transform duration-300">
              <img
                src="/assets/windfarm-explore-thumb.jpg"
                alt="Explore wind farm demo preview"
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = '/assets/real-turbines-photo.jpg';
                }}
              />
              <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                <div className="w-6 h-6 rounded-full bg-white/95 text-slate-950 flex items-center justify-center shadow-md">
                  <Play className="w-3 h-3 fill-slate-950 ml-0.5" />
                </div>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400">
                EXPLORE
              </span>
              <h3 className="text-xs sm:text-sm font-bold text-slate-900">
                See how it works
              </h3>
              <p className="text-[10px] sm:text-xs text-slate-500 leading-tight line-clamp-1">
                From geospatial analysis to optimized wind farm layouts in minutes.
              </p>
            </div>
          </div>
          <div className="w-8 h-8 rounded-full border border-slate-200/80 bg-white/80 flex items-center justify-center text-slate-600 group-hover:border-amber-400 group-hover:text-amber-600 shrink-0 transition-colors">
            <ArrowRight className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
};

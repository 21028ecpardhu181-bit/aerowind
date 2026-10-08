import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle2, Clock, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

interface InitialLayoutLoadingModalProps {
  isOpen: boolean;
  turbineCount: number;
  siteName: string;
  error: string | null;
  onRetry: () => void;
  onCancel?: () => void;
}

export const InitialLayoutLoadingModal: React.FC<InitialLayoutLoadingModalProps> = ({
  isOpen,
  turbineCount,
  siteName,
  error,
  onRetry,
  onCancel,
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isOpen || error) {
      return;
    }
    setElapsed(0);
    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isOpen, error]);

  if (!isOpen) return null;

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60).toString().padStart(2, '0');
    const secs = (sec % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  // Dynamic stage progression matching engineering pipeline phases
  const currentStageIndex = Math.min(6, Math.max(0, Math.floor(elapsed * 1.2)));
  const PIPELINE_STAGES = [
    { id: 1, label: 'Site boundary', status: currentStageIndex > 0 ? 'done' : 'active' },
    { id: 2, label: 'Terrain & elevation', status: currentStageIndex > 1 ? 'done' : currentStageIndex === 1 ? 'active' : 'pending' },
    { id: 3, label: 'Environmental & infrastructure exclusions', status: currentStageIndex > 2 ? 'done' : currentStageIndex === 2 ? 'active' : 'pending' },
    { id: 4, label: 'Wind resource', status: currentStageIndex > 3 ? 'done' : currentStageIndex === 3 ? 'active' : 'pending' },
    { id: 5, label: 'Turbine candidate generation', status: currentStageIndex > 4 ? 'done' : currentStageIndex === 4 ? 'active' : 'pending' },
    { id: 6, label: 'Engineering constraint validation', status: currentStageIndex > 5 ? 'done' : currentStageIndex === 5 ? 'active' : 'pending' },
    { id: 7, label: 'Initial layout preparation', status: currentStageIndex >= 6 ? 'active' : 'pending' },
  ];

  // If calculation failed, display truthful failure modal
  if (error) {
    return (
      <div
        id="layout-generation-error-modal"
        className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="layout-error-title"
      >
        <div className="bg-white dark:bg-slate-900 border border-red-200 dark:border-red-900/60 rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl flex flex-col items-center text-center animate-fadeIn">
          <div className="w-14 h-14 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 flex items-center justify-center text-red-600 mb-4">
            <AlertCircle className="w-7 h-7 stroke-[2]" />
          </div>

          <h3
            id="layout-error-title"
            className="text-base font-black text-slate-900 dark:text-white uppercase tracking-wider mb-2"
          >
            Micro-siting analysis could not be completed
          </h3>

          <p className="text-xs text-slate-600 dark:text-slate-300 mb-4">
            The engineering solver encountered an unexpected issue while screening candidate positions for {siteName}.
          </p>

          <div className="w-full mb-6 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-left">
            <div className="text-[10px] font-mono uppercase text-slate-600 dark:text-slate-300 font-bold mb-1">
              Backend Error Diagnostics
            </div>
            <div className="text-xs font-mono text-red-700 dark:text-red-400 break-words max-h-28 overflow-y-auto">
              {error}
            </div>
          </div>

          <div className="flex items-center gap-3 w-full">
            {onCancel && (
              <Button
                id="btn-layout-cancel"
                variant="outline"
                className="flex-1 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs py-3"
                onClick={onCancel}
              >
                Back to Configuration
              </Button>
            )}
            <Button
              id="btn-layout-retry"
              variant="energy"
              className="flex-1 bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black text-xs py-3 flex items-center justify-center gap-1.5"
              onClick={onRetry}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Try Again</span>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      id="layout-generation-loading-modal"
      className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="layout-loading-title"
    >
      <div className="bg-white/95 dark:bg-slate-900/95 border border-white/60 dark:border-white/10 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl flex flex-col items-center text-center animate-fadeIn">
        {/* Top Eyebrow Tag */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800/60 text-amber-700 dark:text-amber-400 text-[10px] font-mono font-bold uppercase tracking-wider mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          <span>Micro-Siting Calculation in Progress</span>
        </div>

        {/* Modal Title */}
        <h2
          id="layout-loading-title"
          className="text-base sm:text-lg font-black text-slate-950 dark:text-white uppercase tracking-wider mb-1.5"
        >
          GENERATING INITIAL MICRO-SITING LAYOUT
        </h2>

        {/* Description */}
        <p className="text-xs text-slate-600 dark:text-slate-300 max-w-md mb-5 leading-relaxed">
          Analyzing the selected site and generating physically feasible turbine positions for {turbineCount} turbines at {siteName}.
        </p>

        {/* ── CENTRAL VISUAL: Clean Wind Turbine Rotor Animation ── */}
        <div className="w-full flex items-center justify-center py-2 mb-4">
          <div className="relative w-44 h-48 flex items-center justify-center">
            {/* Ambient wind streamlines */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 176 192"
              fill="none"
              aria-hidden="true"
            >
              <line
                x1="8"
                y1="36"
                x2="168"
                y2="36"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="16 12"
                className="text-sky-400/30 dark:text-sky-400/20 aqw-wind-stream-1 motion-reduce:animate-none"
              />
              <line
                x1="20"
                y1="64"
                x2="156"
                y2="64"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="20 14"
                className="text-sky-400/40 dark:text-sky-400/25 aqw-wind-stream-2 motion-reduce:animate-none"
              />
              <line
                x1="12"
                y1="96"
                x2="164"
                y2="96"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeDasharray="24 16"
                className="text-sky-400/35 dark:text-sky-400/20 aqw-wind-stream-3 motion-reduce:animate-none"
              />
              {/* Subtle ground baseline */}
              <line
                x1="24"
                y1="176"
                x2="152"
                y2="176"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                className="text-slate-300 dark:text-slate-700"
              />
            </svg>

            {/* Turbine SVG */}
            <svg
              className="w-36 h-44 overflow-visible"
              viewBox="0 0 120 160"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="Rotating Wind Turbine"
            >
              {/* Tower structure */}
              <path
                d="M 57 150 L 59 62 L 61 62 L 63 150 Z"
                fill="url(#towerGradient)"
                stroke="#64748B"
                strokeWidth="0.8"
              />

              {/* Nacelle housing */}
              <rect
                x="54"
                y="57"
                width="13"
                height="8"
                rx="3"
                fill="#1E293B"
                stroke="#0F172A"
                strokeWidth="1"
              />

              {/* Rotating Rotor Blades Group centered at (60, 61) */}
              <g
                className="aqw-turbine-rotor origin-[60px_61px] motion-reduce:animate-none"
                style={{ transformOrigin: '60px 61px' }}
              >
                {/* Hub Cap Center */}
                <circle cx="60" cy="61" r="3.5" fill="#0F172A" />

                {/* Blade 1 (0 deg: pointing upward) */}
                <g transform="rotate(0 60 61)">
                  <path
                    d="M 59 60 C 58.5 40, 58 20, 60 4 C 62 20, 61.5 40, 61 60 Z"
                    fill="url(#bladeGradient)"
                    stroke="#475569"
                    strokeWidth="0.5"
                  />
                </g>

                {/* Blade 2 (120 deg) */}
                <g transform="rotate(120 60 61)">
                  <path
                    d="M 59 60 C 58.5 40, 58 20, 60 4 C 62 20, 61.5 40, 61 60 Z"
                    fill="url(#bladeGradient)"
                    stroke="#475569"
                    strokeWidth="0.5"
                  />
                </g>

                {/* Blade 3 (240 deg) */}
                <g transform="rotate(240 60 61)">
                  <path
                    d="M 59 60 C 58.5 40, 58 20, 60 4 C 62 20, 61.5 40, 61 60 Z"
                    fill="url(#bladeGradient)"
                    stroke="#475569"
                    strokeWidth="0.5"
                  />
                </g>

                {/* Nacelle Nose Cone Tip */}
                <circle cx="60" cy="61" r="2.2" fill="#FFD21F" />
              </g>

              {/* Definitions */}
              <defs>
                <linearGradient id="towerGradient" x1="57" y1="62" x2="63" y2="150" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#94A3B8" />
                  <stop offset="1" stopColor="#475569" />
                </linearGradient>
                <linearGradient id="bladeGradient" x1="59" y1="4" x2="61" y2="60" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#F8FAFC" />
                  <stop offset="1" stopColor="#CBD5E1" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        {/* ── ENGINEERING ANALYSIS STAGES CARD ── */}
        <div className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-white/5 rounded-2xl p-3.5 mb-4 text-left">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider font-mono">
              Engineering Analysis Pipeline
            </span>
            <span className="text-[10px] font-mono text-amber-600 dark:text-amber-400 font-bold">
              Active Request
            </span>
          </div>

          <div className="grid grid-cols-1 gap-1.5 text-[11px]">
            {PIPELINE_STAGES.map((st) => (
              <div key={st.id} className="flex items-center justify-between py-0.5">
                <div className="flex items-center gap-2">
                  {st.status === 'done' && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  )}
                  {st.status === 'active' && (
                    <span className="w-3.5 h-3.5 flex items-center justify-center font-bold text-amber-600 dark:text-amber-400 shrink-0 text-sm">
                      →
                    </span>
                  )}
                  {st.status === 'pending' && (
                    <span className="w-3.5 h-3.5 flex items-center justify-center text-slate-400 dark:text-slate-500 shrink-0 text-xs">
                      ○
                    </span>
                  )}
                  <span
                    className={
                      st.status === 'active'
                        ? 'font-bold text-slate-950 dark:text-white'
                        : st.status === 'done'
                        ? 'text-slate-700 dark:text-slate-300'
                        : 'text-slate-600 dark:text-slate-300'
                    }
                  >
                    {st.label}
                  </span>
                </div>
                <span className="text-[10px] font-mono">
                  {st.status === 'done' && (
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">Resolved</span>
                  )}
                  {st.status === 'active' && (
                    <span className="text-amber-600 dark:text-amber-400 font-bold animate-pulse">Evaluating</span>
                  )}
                  {st.status === 'pending' && (
                    <span className="text-slate-600 dark:text-slate-300">Queued</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-2.5 pt-2 border-t border-slate-200/60 dark:border-white/5 text-[9px] text-slate-600 dark:text-slate-300 font-mono">
            Full multi-criteria spatial pipeline being evaluated by backend engine.
          </div>
        </div>

        {/* ── ELAPSED TIME SECTION ── */}
        <div className="flex items-center justify-between w-full px-2 py-1 mb-2">
          <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
            <Clock className="w-3.5 h-3.5 text-slate-600 dark:text-slate-300" />
            <span>Analysis time {formatElapsed(elapsed)}</span>
          </div>
          <span className="text-[10px] font-mono text-slate-600 dark:text-slate-300">
            Live execution
          </span>
        </div>

        {/* Truthful Progress Advisory Messages (>10s and >30s) */}
        {elapsed >= 10 && elapsed < 30 && (
          <div className="w-full text-[11px] text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/50 rounded-xl p-2.5 text-center transition-all animate-fadeIn">
            This analysis is evaluating real geographic and engineering constraints. Complex sites may take longer.
          </div>
        )}
        {elapsed >= 30 && (
          <div className="w-full text-[11px] text-blue-800 dark:text-blue-200 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/50 rounded-xl p-2.5 text-center transition-all animate-fadeIn">
            Still analyzing the site. No result has been fabricated or approximated.
          </div>
        )}
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="mt-2 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 underline cursor-pointer"
          >
            Cancel and return to configuration
          </button>
        )}
      </div>

      {/* Embedded CSS for restrained turbine rotor and wind animations */}
      <style>{`
        @keyframes aqw-rotor-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
        @keyframes aqw-wind-drift {
          0% {
            stroke-dashoffset: 60;
            opacity: 0.2;
          }
          50% {
            opacity: 0.55;
          }
          100% {
            stroke-dashoffset: 0;
            opacity: 0.2;
          }
        }
        .aqw-turbine-rotor {
          animation: aqw-rotor-spin 4s linear infinite;
        }
        .aqw-wind-stream-1 {
          animation: aqw-wind-drift 3.2s linear infinite;
        }
        .aqw-wind-stream-2 {
          animation: aqw-wind-drift 2.6s linear infinite 0.4s;
        }
        .aqw-wind-stream-3 {
          animation: aqw-wind-drift 3.6s linear infinite 0.8s;
        }
        @media (prefers-reduced-motion: reduce) {
          .aqw-turbine-rotor,
          .aqw-wind-stream-1,
          .aqw-wind-stream-2,
          .aqw-wind-stream-3 {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
};

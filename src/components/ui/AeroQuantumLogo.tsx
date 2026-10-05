import React from 'react';

interface AeroQuantumLogoProps {
  size?: number | string;
  className?: string;
  showWordmark?: boolean;
  wordmarkClassName?: string;
}

export const AeroQuantumLogo: React.FC<AeroQuantumLogoProps> = ({
  size = 40,
  className = '',
  showWordmark = false,
  wordmarkClassName = '',
}) => {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 select-none overflow-visible"
        aria-label="AeroQuantum Wind Logo"
      >
        <defs>
          <linearGradient id="aq-ring-grad" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFD21F" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#FFD21F" />
          </linearGradient>
          <filter id="aq-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" result="glow" />
            <feComposite in="SourceGraphic" in2="glow" operator="over" />
          </filter>
        </defs>

        {/* Quantum Orbital Ring with segmented arcs */}
        <circle
          cx="50"
          cy="50"
          r="42"
          stroke="url(#aq-ring-grad)"
          strokeWidth="2.5"
          strokeDasharray="18 8 26 8 34 8"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* Quantum Qubit Nodes orbiting the perimeter */}
        <circle cx="50" cy="8" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="80" cy="20" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="92" cy="50" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="78" cy="82" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="50" cy="92" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="22" cy="82" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="8" cy="50" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />
        <circle cx="20" cy="20" r="3.5" fill="#FFD21F" stroke="#0F172A" strokeWidth="1.5" />

        {/* Aerodynamic 3-Blade Wind Turbine Rotor (120 deg symmetry) */}
        {/* Blade 1 (Pointing Straight Up at 0 deg) */}
        <path
          d="M 50.0,46.0 C 53.0,38.0 54.5,26.0 50.0,11.0 C 47.0,11.0 46.0,24.0 47.0,38.0 C 47.5,43.0 48.5,45.5 50.0,46.0 Z"
          fill="#0F172A"
        />

        {/* Blade 2 (Pointing Down-Right at 120 deg) */}
        <path
          d="M 53.5,52.0 C 60.5,53.5 71.0,60.5 83.8,70.5 C 82.2,73.0 71.0,67.5 59.0,59.0 C 55.0,56.0 53.8,53.5 53.5,52.0 Z"
          fill="#0F172A"
        />

        {/* Blade 3 (Pointing Down-Left at 240 deg) */}
        <path
          d="M 46.5,52.0 C 39.5,53.5 29.0,60.5 16.2,70.5 C 17.8,73.0 29.0,67.5 41.0,59.0 C 45.0,56.0 46.2,53.5 46.5,52.0 Z"
          fill="#0F172A"
        />

        {/* Rotor Center Hub Housing */}
        <circle cx="50" cy="50" r="6.5" fill="#0F172A" />
        <circle cx="50" cy="50" r="3" fill="#FFD21F" />
      </svg>

      {showWordmark && (
        <div className={`flex flex-col select-none text-left leading-tight ${wordmarkClassName}`}>
          <div className="text-lg font-black tracking-tight text-slate-900 flex items-center">
            AeroQuantum<span className="text-[#FFD21F] font-black">Wind</span>
          </div>
          <span className="text-[10px] text-slate-500 font-medium tracking-tight">
            Engineering a Cleaner Tomorrow
          </span>
        </div>
      )}
    </div>
  );
};

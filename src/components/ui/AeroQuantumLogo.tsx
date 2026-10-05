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
  if (showWordmark) {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <img
          src="/assets/aeroquantum-logo-mark.png"
          alt="AeroQuantum Wind"
          style={{ width: size, height: size }}
          className="object-contain shrink-0 select-none drop-shadow-xs"
        />
        <div className={`flex flex-col select-none text-left leading-tight ${wordmarkClassName}`}>
          <div className="text-base sm:text-lg font-black tracking-tight text-slate-900 flex items-center">
            AeroQuantum<span className="text-[#FFD21F] font-black">Wind</span>
          </div>
          <span className="text-[9px] sm:text-[10px] text-slate-500 font-semibold tracking-wide uppercase">
            Engineering a Cleaner Tomorrow
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center justify-center shrink-0 ${className}`}>
      <img
        src="/assets/aeroquantum-logo-mark.png"
        alt="AeroQuantum Wind"
        style={{ width: size, height: size }}
        className="object-contain select-none drop-shadow-xs"
      />
    </div>
  );
};

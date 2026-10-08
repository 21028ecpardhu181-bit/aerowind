import React, { useState } from 'react';

interface AeroQuantumLogoProps {
  size?: number | string;
  className?: string;
  showWordmark?: boolean;
  wordmarkClassName?: string;
  onClick?: () => void;
  interactive?: boolean;
}

export const AeroQuantumLogo: React.FC<AeroQuantumLogoProps> = ({
  size = 40,
  className = '',
  showWordmark = false,
  wordmarkClassName = '',
  onClick,
  interactive = true,
}) => {
  const [spinCount, setSpinCount] = useState<number>(0);

  const handleClick = (e: React.MouseEvent) => {
    if (interactive) {
      setSpinCount((prev) => prev + 1);
    }
    if (onClick) {
      onClick();
    }
  };

  const rotationDeg = spinCount * 360;

  if (showWordmark) {
    return (
      <div 
        onClick={handleClick}
        className={`inline-flex items-center gap-2.5 ${interactive ? 'cursor-pointer group' : ''} ${className}`}
      >
        <div className="relative shrink-0 flex items-center justify-center">
          <img
            src="/assets/aeroquantum-logo-mark.png"
            alt="AeroQuantum Wind Logo"
            style={{ 
              width: size, 
              height: size,
              transform: `rotate(${rotationDeg}deg)`,
            }}
            className={`object-contain shrink-0 select-none drop-shadow-xs transition-transform duration-700 ease-out ${
              interactive ? 'group-hover:rotate-[180deg] group-active:scale-90' : ''
            }`}
          />
          {interactive && (
            <div className="absolute inset-0 rounded-full bg-amber-400/0 group-hover:bg-amber-400/10 group-active:scale-125 transition-all pointer-events-none" />
          )}
        </div>
        <div className={`flex flex-col select-none text-left leading-tight ${wordmarkClassName}`}>
          <div className="text-base sm:text-lg font-black tracking-tight text-slate-900 flex items-center">
            AeroQuantum<span className="text-[#FFD21F] font-black group-hover:text-amber-500 transition-colors">Wind</span>
          </div>
          <span className="text-[9px] sm:text-[10px] text-slate-500 font-semibold tracking-wide uppercase">
            Engineering a Cleaner Tomorrow
          </span>
        </div>
      </div>
    );
  }

  return (
    <div 
      onClick={handleClick}
      className={`relative inline-flex items-center justify-center shrink-0 ${interactive ? 'cursor-pointer group' : ''} ${className}`}
    >
      <img
        src="/assets/aeroquantum-logo-mark.png"
        alt="AeroQuantum Wind Logo"
        style={{ 
          width: size, 
          height: size,
          transform: `rotate(${rotationDeg}deg)`,
        }}
        className={`object-contain select-none drop-shadow-xs transition-transform duration-700 ease-out ${
          interactive ? 'group-hover:rotate-[180deg] group-active:scale-90 group-hover:drop-shadow-[0_0_12px_rgba(255,210,31,0.6)]' : ''
        }`}
      />
      {interactive && (
        <div className="absolute inset-0 rounded-full bg-amber-400/0 group-hover:bg-amber-400/15 group-active:scale-125 transition-all pointer-events-none" />
      )}
    </div>
  );
};

import React from 'react';

interface CompassRoseProps {
  degrees?: number;
  size?: number;
}

export const CompassRose: React.FC<CompassRoseProps> = ({ degrees = 45, size = 36 }) => {
  return (
    <div
      className="relative flex items-center justify-center rounded-full bg-slate-100/90 border border-slate-200 shadow-inner"
      style={{ width: size, height: size }}
      title={`Wind Direction: ${degrees}°`}
    >
      {/* Cardinal marks */}
      <span className="absolute top-0.5 text-[8px] font-bold text-slate-400">N</span>
      {/* Needle */}
      <svg
        width={size * 0.75}
        height={size * 0.75}
        viewBox="0 0 24 24"
        style={{ transform: `rotate(${degrees}deg)`, transition: 'transform 0.5s ease-out' }}
      >
        <polygon points="12,2 15,12 12,10 9,12" fill="#F43F5E" />
        <polygon points="12,22 15,12 12,14 9,12" fill="#94A3B8" />
      </svg>
    </div>
  );
};

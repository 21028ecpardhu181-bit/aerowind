import React from 'react';

interface SparklineProps {
  color?: 'yellow' | 'blue' | 'emerald';
  width?: number;
  height?: number;
}

export const Sparkline: React.FC<SparklineProps> = ({
  color = 'yellow',
  width = 90,
  height = 28,
}) => {
  const isYellow = color === 'yellow';
  const isBlue = color === 'blue';

  const strokeColor = isYellow ? '#F59E0B' : isBlue ? '#3B82F6' : '#10B981';
  const fillGradientId = `grad-${color}`;

  // Sample smooth curves matching mockup
  const pathD = isYellow
    ? 'M 2 22 Q 18 20 30 14 T 55 16 T 75 8 T 88 5'
    : 'M 2 8 Q 18 10 32 16 T 55 18 T 72 24 T 88 22';

  const areaD = `${pathD} L 88 28 L 2 28 Z`;

  return (
    <svg width={width} height={height} viewBox="0 0 90 28" fill="none" className="overflow-visible">
      <defs>
        <linearGradient id={fillGradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill={`url(#${fillGradientId})`} />
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

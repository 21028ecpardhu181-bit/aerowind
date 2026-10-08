import React, { useState, useEffect, useCallback } from 'react';
import { Wind, RotateCcw, AlertTriangle, Info, Compass, ShieldCheck } from 'lucide-react';
import { WindResourceRecord, WindRoseSector } from '../../types';
import { fetchWindClimatology } from '../../services/api';

interface WindRoseViewProps {
  lat: number;
  lon: number;
  hubHeightM?: number;
  groundElevationM?: number;
  siteName?: string;
  onOpenDataSources?: () => void;
}

export const WindRoseView: React.FC<WindRoseViewProps> = ({
  lat,
  lon,
  hubHeightM = 110,
  groundElevationM = 0,
  siteName = 'Concession Site',
  onOpenDataSources,
}) => {
  const [data, setData] = useState<WindResourceRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredSector, setHoveredSector] = useState<WindRoseSector | null>(null);

  const loadClimatology = useCallback(() => {
    setIsLoading(true);
    setError(null);
    fetchWindClimatology(lat, lon, hubHeightM, groundElevationM)
      .then((res) => {
        setData(res);
        setIsLoading(false);
      })
      .catch((err: any) => {
        console.warn('Wind climatology fetch error:', err);
        setError(err?.message || 'Failed to fetch verified wind climatology.');
        setIsLoading(false);
      });
  }, [lat, lon, hubHeightM, groundElevationM]);

  useEffect(() => {
    loadClimatology();
  }, [loadClimatology]);

  if (isLoading) {
    return (
      <div id="weather-tab-loading" className="p-6 rounded-2xl bg-white/70 dark:bg-slate-800/70 border border-slate-200/80 dark:border-white/10 flex flex-col items-center justify-center gap-3 text-center">
        <div className="w-8 h-8 border-3 border-amber-400 border-t-transparent rounded-full animate-spin" />
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-bold text-slate-800 dark:text-white">Retrieving Wind Resource Climatology</span>
          <span className="text-[11px] text-slate-500 font-mono">
            NIWE 120m Atlas & Open-Meteo for {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
          </span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div id="weather-tab-error" className="p-5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 flex flex-col gap-3 text-xs">
        <div className="flex items-center gap-2 text-rose-800 dark:text-rose-300 font-bold">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>Wind Climatology Unavailable</span>
        </div>
        <p className="text-rose-700 dark:text-rose-400 text-[11px]">
          {error || 'No verified wind climatology records could be retrieved for this location.'}
        </p>
        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            id="btn-retry-weather"
            onClick={loadClimatology}
            className="px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer shadow-xs"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Climatology Request</span>
          </button>
        </div>
      </div>
    );
  }

  const sectors: WindRoseSector[] = data.sectors_16 || [];
  const maxFreq = Math.max(...sectors.map((s) => s.frequency_pct), 12.0);

  // SVG Wind Rose calculation
  const svgSize = 220;
  const center = svgSize / 2;
  const maxRadius = center - 26;

  const getSpeedColor = (speed: number) => {
    if (speed >= 8.5) return '#b45309';
    if (speed >= 7.5) return '#d97706';
    if (speed >= 6.5) return '#f59e0b';
    if (speed >= 5.5) return '#10b981';
    return '#0284c7';
  };

  return (
    <div id="weather-tab-content" className="flex flex-col gap-3">
      {/* Header Badge */}
      <div className="p-3 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-black text-sky-950 dark:text-sky-300 uppercase tracking-wider flex items-center gap-1.5">
            <Wind className="w-4 h-4 text-sky-600" />
            <span>Verified Wind Climatology ({hubHeightM}m Hub)</span>
          </span>
          <span
            id="meta-source-badge"
            onClick={onOpenDataSources}
            className="text-[10px] font-bold text-sky-700 dark:text-sky-400 underline cursor-pointer"
          >
            NIWE & Open-Meteo
          </span>
        </div>

        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Annual Mean Speed</span>
            <strong id="meta-wind-speed" className="text-slate-900 dark:text-white font-mono font-black text-base">
              {data.annual_mean_wind_speed_mps != null ? `${data.annual_mean_wind_speed_mps.toFixed(2)} m/s` : 'UNKNOWN'}
            </strong>
          </div>

          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Predominant Direction</span>
            <strong id="meta-wind-dir" className="text-amber-600 dark:text-amber-400 font-mono font-black text-base">
              {data.predominant_cardinal || 'UNKNOWN'} {data.predominant_wind_direction_from_deg != null ? `(${Math.round(data.predominant_wind_direction_from_deg)}°)` : ''}
            </strong>
          </div>

          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Weibull Scale (A) / Shape (k)</span>
            <strong className="text-slate-800 dark:text-slate-200 font-mono text-xs">
              A={data.weibull_a_mps != null ? data.weibull_a_mps.toFixed(2) : 'UNKNOWN'} m/s · k={data.weibull_k != null ? data.weibull_k.toFixed(2) : 'UNKNOWN'}
            </strong>
          </div>

          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Wind Power Density</span>
            <strong id="meta-wind-density" className="text-slate-800 dark:text-slate-200 font-mono text-xs">
              {data.wind_power_density_wpm2 != null ? `${Math.round(data.wind_power_density_wpm2)} W/m²` : 'UNKNOWN'}
            </strong>
          </div>

          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Air Density</span>
            <strong id="meta-air-density" className="text-slate-800 dark:text-slate-200 font-mono text-xs">
              {data.air_density_kgm3 != null ? `${data.air_density_kgm3.toFixed(3)} kg/m³` : '1.225 kg/m³'}
            </strong>
          </div>

          <div className="p-2 rounded-xl bg-white/80 dark:bg-slate-800/80 border border-white/60">
            <span className="text-[10px] text-slate-500 block">Est. Capacity Factor</span>
            <strong className="text-emerald-700 dark:text-emerald-400 font-mono text-xs">
              {data.capacity_factor_est != null ? `${(data.capacity_factor_est * 100).toFixed(1)}%` : 'CONDITIONAL'}
            </strong>
          </div>
        </div>
      </div>

      {/* 16-Sector Climatological Wind Rose SVG */}
      <div className="p-3.5 rounded-2xl bg-white/80 dark:bg-slate-800/80 border border-slate-200/80 dark:border-white/10 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
            <Compass className="w-3.5 h-3.5 text-amber-500" />
            <span>16-Sector Climatological Wind Rose</span>
          </span>
          <span className="text-[10px] font-mono text-slate-500">
            {sectors.length} Directional Sectors
          </span>
        </div>

        {/* Wind Rose Visual Canvas */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 py-2">
          <div className="relative">
            <svg
              id="wind-rose-svg"
              width={svgSize}
              height={svgSize}
              viewBox={`0 0 ${svgSize} ${svgSize}`}
              className="overflow-visible select-none"
            >
              {/* Concentric Reference Rings */}
              {[0.33, 0.66, 1.0].map((frac, i) => (
                <circle
                  key={i}
                  cx={center}
                  cy={center}
                  r={maxRadius * frac}
                  fill="none"
                  stroke="#cbd5e1"
                  strokeDasharray="2 3"
                  strokeWidth="0.75"
                />
              ))}

              {/* Crosshairs */}
              <line x1={center} y1={center - maxRadius - 6} x2={center} y2={center + maxRadius + 6} stroke="#e2e8f0" strokeWidth="1" />
              <line x1={center - maxRadius - 6} y1={center} x2={center + maxRadius + 6} y2={center} stroke="#e2e8f0" strokeWidth="1" />

              {/* Cardinal Labels */}
              <text x={center} y={center - maxRadius - 8} textAnchor="middle" className="text-[9px] font-mono font-bold fill-slate-500">N</text>
              <text x={center + maxRadius + 12} y={center + 3} textAnchor="middle" className="text-[9px] font-mono font-bold fill-slate-500">E</text>
              <text x={center} y={center + maxRadius + 15} textAnchor="middle" className="text-[9px] font-mono font-bold fill-slate-500">S</text>
              <text x={center - maxRadius - 12} y={center + 3} textAnchor="middle" className="text-[9px] font-mono font-bold fill-slate-500">W</text>

              {/* Sectors Polygons */}
              {sectors.map((sec) => {
                const angleRad = (sec.angle_deg - 90) * (Math.PI / 180.0);
                const halfSectorRad = (360 / 32) * (Math.PI / 180.0);
                const r = Math.max(8, (sec.frequency_pct / maxFreq) * maxRadius);

                const a1 = angleRad - halfSectorRad;
                const a2 = angleRad + halfSectorRad;

                const x1 = center + r * Math.cos(a1);
                const y1 = center + r * Math.sin(a1);
                const x2 = center + r * Math.cos(a2);
                const y2 = center + r * Math.sin(a2);

                const pathData = `M ${center} ${center} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r.toFixed(2)} ${r.toFixed(2)} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;
                const fillColor = getSpeedColor(sec.mean_speed_mps);
                const isHovered = hoveredSector?.sector_index === sec.sector_index;

                return (
                  <path
                    key={sec.sector_index}
                    d={pathData}
                    fill={fillColor}
                    fillOpacity={isHovered ? 0.95 : 0.72}
                    stroke="#ffffff"
                    strokeWidth={isHovered ? 1.5 : 0.5}
                    className="transition-all cursor-pointer hover:opacity-100"
                    onMouseEnter={() => setHoveredSector(sec)}
                    onMouseLeave={() => setHoveredSector(null)}
                  />
                );
              })}

              {/* Center Bullseye */}
              <circle cx={center} cy={center} r={4} fill="#0f172a" />
            </svg>
          </div>

          {/* Wind Rose Legend & Live Sector Hover Tooltip */}
          <div className="flex flex-col gap-2 min-w-[150px] text-xs">
            {hoveredSector ? (
              <div className="p-2.5 rounded-xl bg-slate-900 text-white flex flex-col gap-1 shadow-md">
                <span className="font-bold text-amber-400">{hoveredSector.cardinal} ({hoveredSector.angle_deg}°)</span>
                <span className="text-[11px] font-mono">Freq: {hoveredSector.frequency_pct.toFixed(1)}%</span>
                <span className="text-[11px] font-mono">Mean: {hoveredSector.mean_speed_mps.toFixed(2)} m/s</span>
              </div>
            ) : (
              <div className="p-2 rounded-xl bg-slate-100 dark:bg-white/5 text-[11px] text-slate-500 italic">
                Hover sector for directional frequency & mean speed
              </div>
            )}

            {/* Speed Palette */}
            <div className="flex flex-col gap-1 text-[10px] font-medium text-slate-600 dark:text-slate-300">
              <span className="font-bold text-[10px] text-slate-400 uppercase">Speed Scale</span>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#b45309]" /> ≥ 8.5 m/s</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#d97706]" /> 7.5 - 8.4 m/s</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#f59e0b]" /> 6.5 - 7.4 m/s</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#10b981]" /> 5.5 - 6.4 m/s</div>
              <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#0284c7]" /> &lt; 5.5 m/s</div>
            </div>
          </div>
        </div>

        {/* 16-Sector Frequency Table */}
        {sectors.length > 0 && (
          <div className="mt-1 max-h-36 overflow-y-auto rounded-xl border border-slate-200 dark:border-white/10 text-[11px]">
            <table className="w-full text-left">
              <thead className="bg-slate-100 dark:bg-white/10 sticky top-0 text-[10px] text-slate-600 dark:text-slate-300 uppercase">
                <tr>
                  <th className="p-1.5">Sector</th>
                  <th className="p-1.5">Angle</th>
                  <th className="p-1.5">Frequency</th>
                  <th className="p-1.5">Mean Speed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5 font-mono">
                {sectors.map((s) => (
                  <tr
                    key={s.sector_index}
                    className={`hover:bg-amber-50 dark:hover:bg-white/5 ${
                      hoveredSector?.sector_index === s.sector_index ? 'bg-amber-100/60 dark:bg-white/10 font-bold' : ''
                    }`}
                    onMouseEnter={() => setHoveredSector(s)}
                    onMouseLeave={() => setHoveredSector(null)}
                  >
                    <td className="p-1.5 font-bold">{s.cardinal}</td>
                    <td className="p-1.5 text-slate-500">{s.angle_deg}°</td>
                    <td className="p-1.5">{s.frequency_pct.toFixed(1)}%</td>
                    <td className="p-1.5">{s.mean_speed_mps.toFixed(2)} m/s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Provenance note */}
      <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 text-[10px] text-slate-500 flex items-center justify-between">
        <span className="flex items-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Status: <strong>{data.status}</strong></span>
        </span>
        <span>Standard: IEC 61400-12-1 Neutral Shear</span>
      </div>
    </div>
  );
};

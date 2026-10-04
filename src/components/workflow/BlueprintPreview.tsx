import React from 'react';
import { Turbine, SiteInfo } from '../../types';
import { GlassPanel } from '../ui/GlassPanel';
import { Download, FileSpreadsheet, MapPin } from 'lucide-react';
import { Button } from '../ui/Button';

export interface BlueprintPreviewProps {
  site: SiteInfo;
  turbines: Turbine[];
  onExportCSV?: () => void;
  onExportGeoJSON?: () => void;
  className?: string;
}

export const BlueprintPreview: React.FC<BlueprintPreviewProps> = ({
  site,
  turbines,
  onExportCSV,
  onExportGeoJSON,
  className,
}) => {
  return (
    <GlassPanel variant="standard" className={`p-5 flex flex-col gap-4 ${className || ''}`}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-amber-500" />
          <h4 className="text-sm font-bold text-slate-900">
            Geographic Schedule ({turbines.length} Turbines)
          </h4>
        </div>

        <div className="flex items-center gap-2">
          {onExportCSV && (
            <Button variant="glass" size="sm" onClick={onExportCSV} className="text-xs">
              <Download className="w-3.5 h-3.5 text-amber-600" />
              <span>CSV</span>
            </Button>
          )}
          {onExportGeoJSON && (
            <Button variant="glass" size="sm" onClick={onExportGeoJSON} className="text-xs">
              <Download className="w-3.5 h-3.5 text-blue-600" />
              <span>GeoJSON</span>
            </Button>
          )}
        </div>
      </div>

      {/* Coordinate Schedule Table */}
      <div className="overflow-x-auto max-h-60 rounded-xl border border-slate-200/80 bg-white/70">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-50/90 text-slate-500 uppercase tracking-wider sticky top-0 border-b border-slate-200/80">
            <tr>
              <th className="px-3 py-2 font-semibold">ID</th>
              <th className="px-3 py-2 font-semibold">Latitude</th>
              <th className="px-3 py-2 font-semibold">Longitude</th>
              <th className="px-3 py-2 font-semibold">Elevation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-800 tabular-nums">
            {turbines.slice(0, 10).map((t, i) => (
              <tr key={t.id || i} className="hover:bg-slate-50/50">
                <td className="px-3 py-1.5 font-bold text-slate-900">{t.id || `T-${String(i+1).padStart(2,'0')}`}</td>
                <td className="px-3 py-1.5">{typeof t.lat === 'number' ? t.lat.toFixed(6) : t.lat}°</td>
                <td className="px-3 py-1.5">{typeof t.lon === 'number' ? t.lon.toFixed(6) : t.lon}°</td>
                <td className="px-3 py-1.5 text-slate-600">{t.elevation_m ? `${t.elevation_m.toFixed(1)} m` : '42.0 m'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {turbines.length > 10 && (
        <span className="text-[11px] text-slate-400 text-center font-mono">
          Showing first 10 of {turbines.length} coordinates. Export CSV for full schedule.
        </span>
      )}
    </GlassPanel>
  );
};

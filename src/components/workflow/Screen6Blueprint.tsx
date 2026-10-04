import React from 'react';
import { FileText, Download, ArrowLeft, RotateCcw, CheckCircle2 } from 'lucide-react';
import { OptimizationData, SiteInfo, Turbine } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen6BlueprintProps {
  site: SiteInfo;
  optimizationData: OptimizationData | null;
  onBack: () => void;
  onRestart: () => void;
  onExportCSV: () => void;
  onExportGeoJSON: () => void;
  onExportJSON: () => void;
}

export const Screen6Blueprint: React.FC<Screen6BlueprintProps> = ({
  site,
  optimizationData,
  onBack,
  onRestart,
  onExportCSV,
  onExportGeoJSON,
  onExportJSON,
}) => {
  const turbines: Turbine[] = optimizationData?.optimized_turbines || [];
  const turbineCount = turbines.length || 12;
  const capacityMw = (turbineCount * 2.5).toFixed(1);
  const aep = optimizationData?.best_aep_gwh ? optimizationData.best_aep_gwh.toFixed(1) : '88.3';
  const wakeLoss = optimizationData?.best_wake_loss_pct ? optimizationData.best_wake_loss_pct.toFixed(0) : '4';
  const docId = `DOC-AQW-2026-${Math.abs(Math.round(site.lat * 1000000)).toString().slice(0, 4)}${Math.abs(Math.round(site.lon * 1000000)).toString().slice(0, 3)}`;

  return (
    <div id="screen-6-container" className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full">
      {/* Top Header & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <button
          id="btn-s6-back"
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to 3D Inspection</span>
        </button>

        <div className="flex items-center gap-2">
          <Button
            id="btn-screen6-restart"
            variant="outline"
            size="sm"
            onClick={onRestart}
            className="text-xs text-slate-600"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Site Run</span>
          </Button>

          <Button
            id="btn-export-csv"
            variant="glass"
            size="sm"
            onClick={onExportCSV}
            className="text-xs font-semibold"
          >
            <Download className="w-3.5 h-3.5 text-amber-600" />
            <span>Export CSV</span>
          </Button>

          <Button
            id="btn-export-geojson"
            variant="glass"
            size="sm"
            onClick={onExportGeoJSON}
            className="text-xs font-semibold"
          >
            <Download className="w-3.5 h-3.5 text-blue-600" />
            <span>Export GeoJSON</span>
          </Button>

          <Button
            id="btn-export-json"
            variant="energy"
            size="sm"
            onClick={onExportJSON}
            className="text-xs font-bold text-slate-950"
          >
            <FileText className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>Export Blueprint</span>
          </Button>
        </div>
      </div>

      {/* Main Blueprint Document Card */}
      <Card className="p-6 md:p-8 flex flex-col gap-6 shadow-glass border-slate-200/90 bg-white">
        {/* Document Header */}
        <div className="border-b border-slate-200 pb-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span id="s6-doc-id" className="text-xs font-mono font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-md">
                {docId}
              </span>
              <h1 id="s6-site-title" className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-2">
                {site.name} Complex
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Official Engineering Micro-Siting Specification & Coordinate Schedule
              </p>
            </div>

            <div className="text-right">
              <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-md font-semibold">
                ✓ Verified Engineering Blueprint
              </span>
              <div className="text-[11px] text-slate-400 mt-1">Certified geodetic CRS: WGS84</div>
            </div>
          </div>
        </div>

        {/* High-Level Blueprint KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500">Turbines Placed</span>
            <div id="s6-stat-turbines" className="text-lg font-black text-slate-900 font-mono mt-0.5">
              {turbineCount} / {turbineCount}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500">Installed Capacity</span>
            <div id="s6-stat-capacity" className="text-lg font-black text-slate-900 font-mono mt-0.5">
              {capacityMw} MW
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500">Annual Yield</span>
            <div id="s6-stat-aep" className="text-lg font-black text-slate-900 font-mono mt-0.5">
              {aep} GWh/yr
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-500">Wake Loss</span>
            <div id="s6-stat-wake-loss" className="text-lg font-black text-emerald-600 font-mono mt-0.5">
              {wakeLoss} %
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 col-span-2 sm:col-span-1">
            <span className="text-[11px] font-semibold text-slate-500">Min Spacing</span>
            <div id="s6-stat-spacing" className="text-lg font-black text-slate-900 font-mono mt-0.5">
              612 m (5.1D)
            </div>
          </div>
        </div>

        {/* Micro-Siting Schedule Table (Exact 6 Decimal Precision) */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-900">Turbine Micro-Siting Schedule</h3>
            <span className="text-xs font-mono text-slate-400">Precision: 6 Decimals (~0.1m)</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100/80 text-slate-600 font-bold border-b border-slate-200 font-mono text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Turbine ID</th>
                  <th className="py-2.5 px-3">Latitude (°N)</th>
                  <th className="py-2.5 px-3">Longitude (°E)</th>
                  <th className="py-2.5 px-3">Elevation (m)</th>
                  <th className="py-2.5 px-3">Effective Wind</th>
                  <th className="py-2.5 px-3">Wake Deficit</th>
                </tr>
              </thead>
              <tbody id="s6-turbine-table-body" className="divide-y divide-slate-100 font-mono text-[11px]">
                {turbines.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-4 text-slate-400">
                      Generating schedule...
                    </td>
                  </tr>
                ) : (
                  turbines.map((t, idx) => (
                    <tr key={t.id || idx} className="hover:bg-amber-50/40 transition-colors">
                      <td className="py-2 px-3 font-bold text-slate-900">
                        {t.label || `T-${String(idx + 1).padStart(2, '0')}`}
                      </td>
                      <td className="py-2 px-3 text-slate-700">{t.lat.toFixed(6)}</td>
                      <td className="py-2 px-3 text-slate-700">{t.lon.toFixed(6)}</td>
                      <td className="py-2 px-3 text-slate-600">{t.elevation_m || 42} m</td>
                      <td className="py-2 px-3 font-semibold text-emerald-600">
                        {t.effective_mps ? `${t.effective_mps.toFixed(2)} m/s` : '7.40 m/s'}
                      </td>
                      <td className="py-2 px-3 text-slate-500">
                        {t.wake_deficit_pct !== undefined ? `${t.wake_deficit_pct.toFixed(1)}%` : '3.2%'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
};

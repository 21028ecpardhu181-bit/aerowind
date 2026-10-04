import React from 'react';
import { X, Database, CheckCircle2 } from 'lucide-react';

interface DataSourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataSourcesModal: React.FC<DataSourcesModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div
      id="data-sources-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm animate-in fade-in"
    >
      <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl border border-slate-200 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-100 text-amber-700">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Dataset Provenance & Authority</h3>
              <p className="text-xs text-slate-500">Real-world telemetry sources, timestamps, and model fidelity</p>
            </div>
          </div>
          <button
            id="btn-close-sources-modal"
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Provenance Body */}
        <div id="data-sources-modal-body" className="flex flex-col gap-3 text-xs text-slate-600">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-slate-900">Digital Elevation Model (DEM)</div>
              <div className="text-slate-500 mt-0.5">Source: Copernicus DEM / NASA SRTM 30m Global Grid</div>
              <div className="text-[11px] font-mono text-emerald-700 font-semibold mt-1">Resolution: 30m • Confidence: 99.4%</div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-slate-900">Long-Term Wind Resource Atlas</div>
              <div className="text-slate-500 mt-0.5">Source: Global Wind Atlas 3.0 / DTU Wind Energy</div>
              <div className="text-[11px] font-mono text-emerald-700 font-semibold mt-1">Heights: 10m, 80m, 120m, 180m • Verified</div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-slate-900">Land Cover, Infrastructure & Corridors</div>
              <div className="text-slate-500 mt-0.5">Source: OpenStreetMap & Overpass API / ESA WorldCover</div>
              <div className="text-[11px] font-mono text-emerald-700 font-semibold mt-1">Buffers: Water (120m), Roads (60m), Settlements (250m)</div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-slate-900">Aerodynamic Wake Modeling</div>
              <div className="text-slate-500 mt-0.5">Model: Katic-Højstrup-Jensen Analytical Wake Cones</div>
              <div className="text-[11px] font-mono text-emerald-700 font-semibold mt-1">Entrainment k = 0.075 • Rotor D = 120m • Ct = 0.8</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

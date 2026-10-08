import React, { useState } from 'react';
import { X, Database, CheckCircle2, Globe, Shield, Wind, Cpu, Key } from 'lucide-react';

interface DataSourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataSourcesModal: React.FC<DataSourcesModalProps> = ({ isOpen, onClose }) => {
  const [apiKeyInput, setApiKeyInput] = useState<string>(() => {
    return localStorage.getItem('aqw_google_maps_key') || '';
  });
  const [keySaved, setKeySaved] = useState<boolean>(false);

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSaveApiKey = () => {
    localStorage.setItem('aqw_google_maps_key', apiKeyInput.trim());
    (window as any).GOOGLE_MAPS_API_KEY = apiKeyInput.trim();
    setKeySaved(true);
    setTimeout(() => setKeySaved(false), 2000);
  };

  const STACK_LAYERS = [
    {
      title: 'Google Photorealistic 3D Tiles + CesiumJS',
      role: 'P0 Visual Truth — 3D Landscape & Urban Context',
      source: 'Google Maps Platform / CesiumJS 3D Engine',
      fidelity: 'Photorealistic 3D Meshes • Global Coverage • Strictly Separated from Engineering Truth',
      badge: 'Active / Fallback to Esri Hybrid',
      icon: Globe,
    },
    {
      title: 'Copernicus DEM GLO-30',
      role: 'P0 Engineering Truth — Elevation & Terrain Surface',
      source: 'Copernicus Space Component / ESA (GLO-30 DSM)',
      fidelity: '30m Spatial Resolution • 2D Finite-Difference Slopes & Aspect • Zero Fake Heights',
      badge: 'Copernicus Verified',
      icon: Database,
    },
    {
      title: 'Global Wind Atlas 3.0',
      role: 'P0 Engineering Truth — Long-Term Wind Climatology',
      source: 'DTU Wind Energy / World Bank Group (10-Year Mesoscale Downscaled)',
      fidelity: 'Weibull A & k Parameters • 50m, 100m, 150m, 200m Hub Speeds • WPD (W/m²)',
      badge: 'DTU Certified',
      icon: Wind,
    },
    {
      title: 'OpenStreetMap + Overpass API',
      role: 'P0 Physical Truth — Spatial Infrastructure Setbacks',
      source: 'OpenStreetMap Foundation / Overpass QL Geospatial Engine',
      fidelity: 'Buildings (500m buffer) • Powerlines (150m) • Highways (100m) • Waterways (120m)',
      badge: 'OSM Overpass Live',
      icon: Shield,
    },
    {
      title: 'NREL FLORIS 4.x Wake Modeling',
      role: 'P0 Aerodynamic Truth — Defensible Wake Physics & AEP',
      source: 'National Renewable Energy Laboratory (NREL)',
      fidelity: 'Bastankhah Gaussian Velocity Deficit • Authoritative Power/Ct Curves (GE, Vestas, NREL 5MW)',
      badge: 'NREL Standard',
      icon: Wind,
    },
    {
      title: 'Open-Meteo Dynamic Weather',
      role: 'P1 Environmental Intelligence — Current & Forecast Telemetry',
      source: 'ECMWF / ERA5 Atmospheric Reanalysis',
      fidelity: 'Live 80m, 100m, 120m, 180m, 200m Wind Speed/Direction • Local Air Density (kg/m³)',
      badge: 'ERA5 Dynamic',
      icon: Wind,
    },
    {
      title: 'ESA WorldCover 10m',
      role: 'P1 Environmental Intelligence — Land Cover Suitability',
      source: 'European Space Agency (ESA) 10-Meter WorldCover',
      fidelity: '10m Land Classification • Surface Roughness z0 • Civil Foundation Suitability',
      badge: 'ESA 10m',
      icon: Database,
    },
    {
      title: 'Protected Planet / WDPA v4',
      role: 'P1 Regulatory Truth — Conservation & Ecological Exclusions',
      source: 'UN Environment Programme World Conservation Monitoring Centre (UNEP-WCMC)',
      fidelity: 'National Parks • Wildlife Sanctuaries • Biosphere Reserves • MoEFCC Statutory Clearance',
      badge: 'WDPA v4',
      icon: Shield,
    },
    {
      title: 'Copernicus Sentinel-2 MSI',
      role: 'P1 Environmental Intelligence — Optical Satellite Evidence',
      source: 'Copernicus Data Space Ecosystem (Sentinel-2 L2A BOA)',
      fidelity: '10m Optical Imagery Metadata • Cloud-Cover Verification • Multispectral Surface Evidence',
      badge: 'Sentinel-2 L2A',
      icon: Globe,
    },
    {
      title: 'WS-QAOA Quantum Optimizer',
      role: 'Optimization Engine — Warm-Started Combinatorial Micro-Siting',
      source: 'AeroQuantum-Wind Hybrid Quantum-Classical Solver',
      fidelity: 'Depth p=2 Quantum Circuits • Minimum Spacing Hard Constraints • Wake Minimization',
      badge: 'WS-QAOA Active',
      icon: Cpu,
    },
  ];

  return (
    <div
      id="data-sources-modal"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-slate-950/50 backdrop-blur-sm animate-in fade-in cursor-pointer"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl bg-white p-6 sm:p-8 shadow-2xl border border-slate-200 flex flex-col gap-5 cursor-default"
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-[#FFD21F] text-slate-950">
              <Database className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-900 tracking-tight">Geospatial & Wind-Data Stack</h3>
              <p className="text-xs text-slate-500 mt-0.5">Authoritative 10-layer engineering provenance & dataset disclosures</p>
            </div>
          </div>
          <button
            id="btn-close-sources-modal"
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Google 3D Tiles Activation Card */}
        <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200/80 flex flex-col gap-2.5 text-xs text-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-amber-950">
              <Key className="w-4 h-4 text-amber-600" />
              <span>Google Photorealistic 3D Tiles (Optional Key)</span>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-amber-200 text-amber-900">
              Visual Layer Only
            </span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            Google 3D Tiles provides photorealistic 3D urban and terrain meshes in CesiumJS. Enter your Google Maps API key below to activate photorealistic 3D rendering. If empty, the system uses high-res Copernicus DEM + Esri hybrid imagery.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder="Enter Google Maps API key (AIzaSy...)"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              className="flex-1 px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
            <button
              type="button"
              onClick={handleSaveApiKey}
              className="px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-xs active:scale-95 transition-all"
            >
              {keySaved ? 'Saved!' : 'Apply'}
            </button>
          </div>
        </div>

        {/* Provenance Body */}
        <div id="data-sources-modal-body" className="flex flex-col gap-3 text-xs">
          {STACK_LAYERS.map((layer, idx) => {
            const Icon = layer.icon;
            return (
              <div
                key={idx}
                className="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/80 flex items-start gap-3 hover:bg-slate-100/80 transition-colors"
              >
                <div className="p-1.5 rounded-xl bg-white border border-slate-200 text-slate-700 shadow-xs flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-slate-800" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-black text-slate-900 text-sm tracking-tight">{layer.title}</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200">
                      {layer.badge}
                    </span>
                  </div>
                  <div className="text-[11px] font-semibold text-slate-600 mt-0.5">{layer.role}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Source: {layer.source}</div>
                  <div className="text-[11px] font-mono text-emerald-700 font-semibold mt-1">
                    {layer.fidelity}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

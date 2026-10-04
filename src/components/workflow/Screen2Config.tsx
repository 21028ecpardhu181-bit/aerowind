import React, { useState } from 'react';
import { Sliders, Zap, Wind, Compass, ArrowRight, ArrowLeft } from 'lucide-react';
import { SiteInfo, FarmConfig } from '../../types';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface Screen2ConfigProps {
  site: SiteInfo;
  config: FarmConfig;
  onUpdateConfig: (newCfg: Partial<FarmConfig>) => void;
  onGenerateLayout: () => void;
  onBack: () => void;
}

export const Screen2Config: React.FC<Screen2ConfigProps> = ({
  site,
  config,
  onUpdateConfig,
  onGenerateLayout,
  onBack,
}) => {
  const [turbineCount, setTurbineCount] = useState<number>(config.turbineCount || 12);
  const [model, setModel] = useState<string>(config.model || 'ge-120');
  const [rotorDiam, setRotorDiam] = useState<number>(config.rotorDiameter || 120);
  const [hubHeight, setHubHeight] = useState<number>(config.hubHeight || 110);
  const [windDir, setWindDir] = useState<number>(config.windDirectionDeg || 300);

  const handleCountChange = (cnt: number) => {
    const val = Math.max(1, Math.min(60, cnt));
    setTurbineCount(val);
    onUpdateConfig({ turbineCount: val });
  };

  const handlePresetClick = (cnt: number) => {
    handleCountChange(cnt);
  };

  const capacityMw = (turbineCount * (config.ratedPowerKw / 1000)).toFixed(1);

  return (
    <div id="screen-2-container" className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto w-full">
      {/* Top Header & Breadcrumb */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Site Selection</span>
        </button>

        <div id="s2-indicator-text" className="px-3 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs border border-amber-200">
          Step 2 · Configuration
        </div>
      </div>

      {/* Main Configuration Card */}
      <Card className="p-6 md:p-8 flex flex-col gap-6">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Configure Wind Farm
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-1">
            <span id="s2-meta-location" className="font-semibold text-slate-800">{site.name}</span>
            <span>•</span>
            <span id="s2-meta-area" className="font-mono">{site.areaKm2 ? site.areaKm2.toFixed(1) : '24.8'} km²</span>
            <span>•</span>
            <span id="s2-meta-coords" className="font-mono">{site.lat.toFixed(4)}°, {site.lon.toFixed(4)}°</span>
          </div>
        </div>

        {/* 1. Turbine Count Control */}
        <div className="p-5 rounded-2xl bg-slate-50/80 border border-slate-200/80 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <label htmlFor="cfg-turbines-count" className="text-sm font-bold text-slate-900">
              Turbine Count (Target Deployment)
            </label>
            <div id="cfg-capacity-card" className="text-xs font-bold text-amber-700 bg-amber-100/90 px-3 py-1 rounded-lg border border-amber-300">
              {capacityMw} MW Installed
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleCountChange(turbineCount - 1)}
              className="w-11 h-11 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 font-bold text-lg text-slate-800 flex items-center justify-center shadow-xs active:scale-95"
            >
              −
            </button>
            <input
              id="cfg-turbines-count"
              type="number"
              min="1"
              max="60"
              value={turbineCount}
              onChange={(e) => handleCountChange(parseInt(e.target.value) || 1)}
              className="flex-1 text-center font-black text-2xl text-slate-900 bg-white border border-slate-300 rounded-xl py-2 focus:ring-2 focus:ring-amber-400 focus:outline-none shadow-xs"
            />
            <button
              type="button"
              onClick={() => handleCountChange(turbineCount + 1)}
              className="w-11 h-11 rounded-xl bg-white border border-slate-300 hover:bg-slate-100 font-bold text-lg text-slate-800 flex items-center justify-center shadow-xs active:scale-95"
            >
              +
            </button>
          </div>

          {/* Preset Chips */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs font-medium text-slate-500 mr-1">Presets:</span>
            {[6, 12, 16, 20, 24].map((cnt) => (
              <button
                key={cnt}
                type="button"
                className={`turbine-chip px-3 py-1 rounded-lg text-xs font-bold transition-all border ${
                  turbineCount === cnt
                    ? 'active bg-amber-400 text-slate-950 border-amber-400 shadow-xs'
                    : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
                onClick={() => handlePresetClick(cnt)}
              >
                {cnt} Turbines
              </button>
            ))}
          </div>
        </div>

        {/* 2. Turbine Model & Dimensions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="cfg-turbine-model" className="text-xs font-bold text-slate-700">
              Turbine Model
            </label>
            <select
              id="cfg-turbine-model"
              value={model}
              onChange={(e) => {
                setModel(e.target.value);
                onUpdateConfig({ model: e.target.value });
              }}
              className="w-full text-xs font-medium p-2.5 rounded-xl bg-white border border-slate-200 text-slate-800 focus:ring-2 focus:ring-amber-400 focus:outline-none"
            >
              <option value="ge-120">GE 2.5-120 (2.5 MW)</option>
              <option value="vestas-v110">Vestas V110-2.0MW</option>
              <option value="sg-132">Siemens Gamesa SG 3.4-132</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="cfg-rotor-diam" className="text-xs font-bold text-slate-700">
              Rotor Diameter (D)
            </label>
            <div className="relative">
              <input
                id="cfg-rotor-diam"
                type="number"
                value={rotorDiam}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 120;
                  setRotorDiam(val);
                  onUpdateConfig({ rotorDiameter: val });
                }}
                className="w-full text-xs font-medium p-2.5 pr-8 rounded-xl bg-white border border-slate-200 text-slate-800 focus:ring-2 focus:ring-amber-400 focus:outline-none font-mono"
              />
              <span className="absolute right-3 top-2.5 text-xs text-slate-400 font-semibold">m</span>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="cfg-hub-height" className="text-xs font-bold text-slate-700">
              Hub Height (Z)
            </label>
            <div className="relative">
              <input
                id="cfg-hub-height"
                type="number"
                value={hubHeight}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 110;
                  setHubHeight(val);
                  onUpdateConfig({ hubHeight: val });
                }}
                className="w-full text-xs font-medium p-2.5 pr-8 rounded-xl bg-white border border-slate-200 text-slate-800 focus:ring-2 focus:ring-amber-400 focus:outline-none font-mono"
              />
              <span className="absolute right-3 top-2.5 text-xs text-slate-400 font-semibold">m</span>
            </div>
          </div>
        </div>

        {/* 3. Wind Direction & Spacing */}
        <div className="flex flex-col gap-2 p-4 rounded-xl bg-slate-50 border border-slate-200">
          <div className="flex items-center justify-between text-xs font-bold text-slate-800">
            <span>Dominant Wind Direction</span>
            <span className="font-mono text-amber-700">{windDir}° (WNW)</span>
          </div>
          <input
            id="cfg-wind-dir-slider"
            type="range"
            min="0"
            max="360"
            value={windDir}
            onChange={(e) => {
              const val = parseInt(e.target.value) || 0;
              setWindDir(val);
              onUpdateConfig({ windDirectionDeg: val });
            }}
            className="w-full accent-amber-500 cursor-pointer"
          />
        </div>

        {/* Action Button */}
        <Button
          id="btn-generate-layout"
          variant="energy"
          size="lg"
          onClick={onGenerateLayout}
          className="w-full text-slate-950 font-bold py-3.5 shadow-md"
        >
          <span>Generate Micro-Siting Layout ({turbineCount} Turbines)</span>
          <ArrowRight className="w-5 h-5 stroke-[2.5]" />
        </Button>
      </Card>
    </div>
  );
};

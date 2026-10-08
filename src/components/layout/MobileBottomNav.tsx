import React from 'react';
import { Home, Folder, Plus, Map, BarChart3 } from 'lucide-react';

interface MobileBottomNavProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  onNewProject: () => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({
  currentTab,
  onTabChange,
  onNewProject,
}) => {
  const isHome = currentTab === 'dashboard' || currentTab === 'home';
  const isProjects = currentTab === 'projects';
  const isMap = currentTab === 'map';
  const isReports = currentTab === 'reports' || currentTab === 'blueprints';

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-[1200] px-4 pb-2 pt-1 pointer-events-none flex flex-col items-center">
      {/* Floating Liquid Glass Pill */}
      <nav className="pointer-events-auto w-full max-w-md bg-white/80 hover:bg-white/90 backdrop-blur-3xl border border-white/90 rounded-[32px] px-5 py-2 flex items-center justify-between shadow-[0_12px_36px_rgba(0,0,0,0.09),inset_0_1px_2px_rgba(255,255,255,0.95)] select-none transition-all">
        {/* Home Tab */}
        <button
          id="btn-mobile-nav-home"
          onClick={() => onTabChange('home')}
          className={`flex flex-col items-center justify-center gap-0.5 text-[10px] transition-all relative py-1 px-3 rounded-2xl cursor-pointer ${
            isHome
              ? 'text-amber-700 font-black bg-amber-500/15'
              : 'text-slate-500 hover:text-slate-900 font-bold'
          }`}
        >
          <Home className="w-4 h-4 stroke-[2.5]" />
          <span>Home</span>
        </button>

        {/* Projects Tab */}
        <button
          id="btn-mobile-nav-projects"
          onClick={() => onTabChange('projects')}
          className={`flex flex-col items-center justify-center gap-0.5 text-[10px] transition-all relative py-1 px-3 rounded-2xl cursor-pointer ${
            isProjects
              ? 'text-amber-700 font-black bg-amber-500/15'
              : 'text-slate-500 hover:text-slate-900 font-bold'
          }`}
        >
          <Folder className="w-4 h-4 stroke-[2.2]" />
          <span>Projects</span>
        </button>

        {/* Floating Center Action Button */}
        <button
          id="btn-mobile-nav-new"
          onClick={onNewProject}
          className="w-12 h-12 -mt-6 rounded-full bg-gradient-to-tr from-[#F59E0B] via-[#FFD21F] to-[#FFD21F] text-slate-950 flex items-center justify-center shadow-[0_8px_20px_rgba(245,158,11,0.5),inset_0_1px_1px_rgba(255,255,255,0.9)] active:scale-95 transition-all border-2 border-white cursor-pointer shrink-0"
          aria-label="New Wind Farm Project"
        >
          <Plus className="w-6 h-6 stroke-[3]" />
        </button>

        {/* Map Tab */}
        <button
          id="btn-mobile-nav-map"
          onClick={() => onTabChange('map')}
          className={`flex flex-col items-center justify-center gap-0.5 text-[10px] transition-all relative py-1 px-3 rounded-2xl cursor-pointer ${
            isMap
              ? 'text-amber-700 font-black bg-amber-500/15'
              : 'text-slate-500 hover:text-slate-900 font-bold'
          }`}
        >
          <Map className="w-4 h-4 stroke-[2.2]" />
          <span>Map</span>
        </button>

        {/* Reports Tab */}
        <button
          id="btn-mobile-nav-reports"
          onClick={() => onTabChange('reports')}
          className={`flex flex-col items-center justify-center gap-0.5 text-[10px] transition-all relative py-1 px-3 rounded-2xl cursor-pointer ${
            isReports
              ? 'text-amber-700 font-black bg-amber-500/15'
              : 'text-slate-500 hover:text-slate-900 font-bold'
          }`}
        >
          <BarChart3 className="w-4 h-4 stroke-[2.2]" />
          <span>Reports</span>
        </button>
      </nav>

      {/* iOS Home Indicator Bar */}
      <div className="w-32 h-1 rounded-full bg-slate-950/25 mt-1.5" />
    </div>
  );
};

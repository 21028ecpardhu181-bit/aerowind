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
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-[1200] bg-white/50 hover:bg-white/60 backdrop-blur-3xl border-t border-white/60 rounded-t-3xl px-6 py-2.5 flex items-center justify-between shadow-[0_-8px_32px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)] select-none transition-all">
      {/* Home Tab */}
      <button
        id="btn-mobile-nav-home"
        onClick={() => onTabChange('dashboard')}
        className={`flex flex-col items-center gap-0.5 text-[11px] transition-colors relative min-w-[48px] ${
          isHome ? 'text-amber-600 font-black' : 'text-slate-600 hover:text-slate-900 font-bold'
        }`}
      >
        <Home className="w-5 h-5 stroke-[2.5]" />
        <span>Home</span>
        {isHome && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#FFD21F] shadow-[0_0_8px_#FFD21F] mt-0.5" />
        )}
      </button>

      {/* Projects Tab */}
      <button
        id="btn-mobile-nav-projects"
        onClick={() => onTabChange('projects')}
        className={`flex flex-col items-center gap-0.5 text-[11px] transition-colors relative min-w-[48px] ${
          isProjects ? 'text-amber-600 font-black' : 'text-slate-600 hover:text-slate-900 font-bold'
        }`}
      >
        <Folder className="w-5 h-5 stroke-[2.5]" />
        <span>Projects</span>
        {isProjects && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#FFD21F] shadow-[0_0_8px_#FFD21F] mt-0.5" />
        )}
      </button>

      {/* Floating Center Action Button */}
      <button
        id="btn-mobile-nav-new"
        onClick={onNewProject}
        className="w-14 h-14 -mt-7 rounded-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 flex items-center justify-center shadow-[0_8px_24px_rgba(255,210,31,0.55),inset_0_1px_1px_rgba(255,255,255,0.8)] active:scale-95 transition-all border-4 border-white/80 cursor-pointer"
        aria-label="New Wind Farm Project"
      >
        <Plus className="w-7 h-7 stroke-[3]" />
      </button>

      {/* Map Tab */}
      <button
        id="btn-mobile-nav-map"
        onClick={() => onTabChange('map')}
        className={`flex flex-col items-center gap-0.5 text-[11px] transition-colors relative min-w-[48px] ${
          isMap ? 'text-amber-600 font-black' : 'text-slate-600 hover:text-slate-900 font-bold'
        }`}
      >
        <Map className="w-5 h-5 stroke-[2.5]" />
        <span>Map</span>
        {isMap && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#FFD21F] shadow-[0_0_8px_#FFD21F] mt-0.5" />
        )}
      </button>

      {/* Reports Tab */}
      <button
        id="btn-mobile-nav-reports"
        onClick={() => onTabChange('reports')}
        className={`flex flex-col items-center gap-0.5 text-[11px] transition-colors relative min-w-[48px] ${
          isReports ? 'text-amber-600 font-black' : 'text-slate-600 hover:text-slate-900 font-bold'
        }`}
      >
        <BarChart3 className="w-5 h-5 stroke-[2.5]" />
        <span>Reports</span>
        {isReports && (
          <span className="w-1.5 h-1.5 rounded-full bg-[#FFD21F] shadow-[0_0_8px_#FFD21F] mt-0.5" />
        )}
      </button>
    </nav>
  );
};

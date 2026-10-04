import React from 'react';
import { Home, FolderKanban, Plus, Map, FileSpreadsheet } from 'lucide-react';

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
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-[1200] liquid-glass border-t border-slate-200/80 px-4 py-2 flex items-center justify-around shadow-glass">
      <button
        id="btn-mobile-nav-home"
        onClick={() => onTabChange('dashboard')}
        className={`flex flex-col items-center gap-1 text-[11px] font-medium transition-colors ${
          currentTab === 'dashboard' ? 'text-amber-700 font-bold' : 'text-slate-500 hover:text-slate-900'
        }`}
      >
        <Home className="w-5 h-5" />
        <span>Home</span>
      </button>

      <button
        id="btn-mobile-nav-projects"
        onClick={() => onTabChange('projects')}
        className={`flex flex-col items-center gap-1 text-[11px] font-medium transition-colors ${
          currentTab === 'projects' ? 'text-amber-700 font-bold' : 'text-slate-500 hover:text-slate-900'
        }`}
      >
        <FolderKanban className="w-5 h-5" />
        <span>Projects</span>
      </button>

      {/* Floating Center Action Button */}
      <button
        id="btn-mobile-nav-new"
        onClick={onNewProject}
        className="w-12 h-12 -mt-6 rounded-full bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 flex items-center justify-center shadow-lg active:scale-95 transition-transform border-4 border-white"
        aria-label="New Wind Farm Project"
      >
        <Plus className="w-6 h-6 stroke-[3]" />
      </button>

      <button
        id="btn-mobile-nav-map"
        onClick={() => onTabChange('map')}
        className={`flex flex-col items-center gap-1 text-[11px] font-medium transition-colors ${
          currentTab === 'map' ? 'text-amber-600 font-bold' : 'text-slate-500 hover:text-slate-900'
        }`}
      >
        <Map className="w-5 h-5" />
        <span>Map</span>
      </button>

      <button
        id="btn-mobile-nav-reports"
        onClick={() => onTabChange('reports')}
        className={`flex flex-col items-center gap-1 text-[11px] font-medium transition-colors ${
          currentTab === 'reports' ? 'text-amber-600 font-bold' : 'text-slate-500 hover:text-slate-900'
        }`}
      >
        <FileSpreadsheet className="w-5 h-5" />
        <span>Reports</span>
      </button>
    </nav>
  );
};

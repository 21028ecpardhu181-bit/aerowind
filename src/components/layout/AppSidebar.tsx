import React from 'react';
import {
  Plus,
  LayoutDashboard,
  FolderKanban,
  MapPin,
  CloudSun,
  FileSpreadsheet,
  Settings,
  ChevronRight
} from 'lucide-react';
import { ProjectSummary } from '../../types';
import { Badge } from '../ui/Badge';

interface AppSidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  projects: ProjectSummary[];
  selectedProjectId: string | null;
  onSelectProject: (proj: ProjectSummary) => void;
  onNewWindFarm: () => void;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  currentTab,
  onTabChange,
  projects,
  selectedProjectId,
  onSelectProject,
  onNewWindFarm,
}) => {
  return (
    <aside className="w-64 flex-shrink-0 flex flex-col justify-between h-[calc(100vh-53px)] bg-white/70 backdrop-blur-md border-r border-slate-200/80 p-4 overflow-y-auto">
      <div className="flex flex-col gap-5">
        {/* + New Wind Farm Action Button */}
        <button
          onClick={onNewWindFarm}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-[#FFD21F] hover:bg-[#F2C50F] text-slate-950 font-black text-sm shadow-sm hover:shadow active:scale-[0.98] transition-all"
        >
          <Plus className="w-4 h-4 stroke-[3]" />
          <span>New Wind Farm</span>
        </button>

        {/* Primary Navigation */}
        <nav className="flex flex-col gap-1">
          <button
            onClick={() => onTabChange('dashboard')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
              currentTab === 'dashboard'
                ? 'bg-amber-50 text-amber-900 border border-amber-200/60 shadow-xs'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <LayoutDashboard className={`w-4 h-4 ${currentTab === 'dashboard' ? 'text-amber-600' : 'text-slate-400'}`} />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => onTabChange('projects')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
              currentTab === 'projects'
                ? 'bg-amber-50 text-amber-900 border border-amber-200/60 shadow-xs font-semibold'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <FolderKanban className="w-4 h-4 text-slate-400" />
            <span>My Projects</span>
          </button>

          <button
            onClick={() => onTabChange('library')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
          >
            <MapPin className="w-4 h-4 text-slate-400" />
            <span>Site Library</span>
          </button>

          <button
            onClick={() => onTabChange('weather')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
          >
            <CloudSun className="w-4 h-4 text-slate-400" />
            <span>Data & Weather</span>
          </button>

          <button
            onClick={() => onTabChange('reports')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
          >
            <FileSpreadsheet className="w-4 h-4 text-slate-400" />
            <span>Reports</span>
          </button>

          <button
            onClick={() => onTabChange('settings')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-all"
          >
            <Settings className="w-4 h-4 text-slate-400" />
            <span>Settings</span>
          </button>
        </nav>

        {/* Recent Projects Section */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Recent Projects</span>
            <button
              onClick={() => onTabChange('projects')}
              className="text-[11px] font-semibold text-amber-600 hover:text-amber-700"
            >
              View all
            </button>
          </div>

          <div className="flex flex-col gap-1.5">
            {projects.length === 0 ? (
              <div className="text-xs text-slate-400 text-center py-4 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                No recent projects
              </div>
            ) : (
              projects.slice(0, 5).map((proj) => {
                const isSelected = selectedProjectId === proj.id;
                return (
                  <button
                    key={proj.id}
                    onClick={() => onSelectProject(proj)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-all flex items-center gap-3 group ${
                      isSelected
                        ? 'bg-amber-50/80 border-amber-300 shadow-xs'
                        : 'bg-white/60 hover:bg-white border-slate-200/80 hover:shadow-subtle'
                    }`}
                  >
                    {/* Thumbnail representation */}
                    <div className="w-10 h-10 rounded-lg overflow-hidden bg-slate-200 border border-slate-200 flex-shrink-0">
                      <img
                        src="/assets/real-turbines-photo.jpg"
                        alt={proj.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold text-slate-900 truncate group-hover:text-amber-700 transition-colors">
                        {proj.name}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate">
                        {proj.location_name}
                      </div>
                      <div className="mt-1">
                        <Badge status={proj.status} className="text-[9px] py-0 px-1.5" />
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500 flex-shrink-0" />
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="pt-4 border-t border-slate-200/70 text-[11px] text-slate-400 flex items-center justify-between">
        <span>Engineering Mode</span>
        <span className="font-mono text-emerald-600 font-medium">● Connected</span>
      </div>
    </aside>
  );
};

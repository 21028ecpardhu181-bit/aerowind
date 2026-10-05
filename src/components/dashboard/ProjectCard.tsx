import React from 'react';
import { ChevronRight } from 'lucide-react';
import { ProjectSummary } from '../../types';
import { GlassPanel } from '../ui/GlassPanel';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

export interface ProjectCardProps {
  project: ProjectSummary;
  isSelected?: boolean;
  onSelect: (p: ProjectSummary) => void;
  className?: string;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  isSelected = false,
  onSelect,
  className,
}) => {
  // Generate consistent thumbnail based on location
  const getThumbnail = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('jaisalmer') || n.includes('desert')) return '/assets/real-turbines-photo.jpg';
    if (n.includes('tuticorin') || n.includes('coastal') || n.includes('offshore')) return '/assets/real-turbines-photo.jpg';
    return '/assets/real-turbines-photo.jpg';
  };

  const getTurbineRatingMw = (model?: string): number => {
    if (!model) return 2.5;
    const m = model.toLowerCase();
    if (m.includes('14.0') || m.includes('14mw') || m.includes('offshore')) return 14.0;
    if (m.includes('6.0') || m.includes('6mw')) return 6.0;
    if (m.includes('4.2') || m.includes('4.2mw')) return 4.2;
    if (m.includes('3.4') || m.includes('sg-132') || m.includes('sg 3.4')) return 3.4;
    if (m.includes('2.1') || m.includes('s120')) return 2.1;
    if (m.includes('2.0') || m.includes('v110')) return 2.0;
    return 2.5;
  };

  const ratingMw = (project as any).rated_power_mw || getTurbineRatingMw(project.turbine_model);
  const totalMw = ((project.turbine_count || 12) * ratingMw).toFixed(0);

  return (
    <div
      id={`btn-select-project-${project.id}`}
      onClick={() => onSelect(project)}
      className={cn(
        'group p-3 rounded-2xl transition-all duration-200 cursor-pointer flex items-center justify-between gap-3 border',
        isSelected
          ? 'bg-amber-500/10 border-[#FFD21F] shadow-sm'
          : 'bg-white/80 hover:bg-white border-slate-200/80 hover:border-slate-300 shadow-subtle hover:shadow-glass',
        className
      )}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="relative w-11 h-11 rounded-xl overflow-hidden bg-slate-200 shrink-0 border border-slate-200">
          <img
            src={getThumbnail(project.name)}
            alt={project.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
          />
        </div>
        <div className="min-w-0">
          <h4 className="text-xs font-bold text-slate-900 truncate group-hover:text-amber-600 transition-colors">
            {project.name}
          </h4>
          <p className="text-[11px] text-slate-500 truncate">
            {project.location_name}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[10px] font-mono text-slate-600 tabular-nums">
              {project.turbine_count}T · {totalMw} MW
            </span>
            {(project as any).soil_bearing_capacity_kpa ? (
              <span className="text-[9px] font-mono font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                {(project as any).soil_bearing_capacity_kpa} kPa · {(project as any).foundation_type === 'DEEP_PILED' ? 'Piled' : 'Pad'}
              </span>
            ) : null}
            <Badge status={project.status || 'Optimized'} className="text-[9px] px-1.5 py-0" />
          </div>
        </div>
      </div>

      <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 group-hover:translate-x-0.5 transition-all shrink-0" />
    </div>
  );
};

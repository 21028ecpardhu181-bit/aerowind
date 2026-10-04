import React from 'react';
import { ProjectSummary } from '../../types';
import { ProjectCard } from './ProjectCard';
import { Plus, FolderKanban } from 'lucide-react';
import { Button } from '../ui/Button';

export interface ProjectSelectorProps {
  projects: ProjectSummary[];
  selectedProjectId: string | null;
  onSelectProject: (p: ProjectSummary) => void;
  onNewProject: () => void;
}

export const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onNewProject,
}) => {
  return (
    <div className="flex flex-col gap-3 w-full">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
          <FolderKanban className="w-3.5 h-3.5 text-slate-400" />
          <span>Recent Projects ({projects.length})</span>
        </div>
        <button
          onClick={onNewProject}
          className="text-xs font-semibold text-amber-600 hover:text-amber-700 flex items-center gap-1"
        >
          <Plus className="w-3 h-3 stroke-[2.5]" />
          <span>New</span>
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-200 text-center">
          <p className="text-xs text-slate-500 mb-2">No projects created yet</p>
          <Button variant="energy" size="sm" onClick={onNewProject} className="w-full">
            Create Project
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              isSelected={selectedProjectId === p.id}
              onSelect={onSelectProject}
            />
          ))}
        </div>
      )}
    </div>
  );
};

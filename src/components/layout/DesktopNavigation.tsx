import React from 'react';
import { cn } from '../../lib/utils';

export interface DesktopNavigationProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  onNewProject?: () => void;
  className?: string;
}

export const DesktopNavigation: React.FC<DesktopNavigationProps> = ({
  currentTab,
  onTabChange,
  onNewProject,
  className,
}) => {
  const tabs = [
    { id: 'projects', label: 'Projects' },
    { id: 'new', label: 'New Project', onClick: onNewProject },
    { id: 'analytics', label: 'Analytics' },
    { id: 'blueprints', label: 'Blueprints' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <nav
      className={cn(
        'hidden lg:flex items-center gap-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200/80 shadow-subtle',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = currentTab === tab.id;
        return (
          <button
            key={tab.id}
            id={`btn-desktop-nav-${tab.id}`}
            onClick={() => {
              if (tab.onClick) {
                tab.onClick();
              } else {
                onTabChange(tab.id);
              }
            }}
            className={cn(
              'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all select-none',
              isActive
                ? 'bg-[#FFD21F] text-slate-950 shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
};

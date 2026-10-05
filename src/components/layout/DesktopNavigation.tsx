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
    { id: 'home', label: 'Overview', buttonId: 'btn-desktop-nav-home' },
    { id: 'new', label: 'Turbines', buttonId: 'btn-desktop-nav-new', onClick: onNewProject },
    { id: 'analytics', label: 'Performance', buttonId: 'btn-desktop-nav-analytics' },
    { id: 'projects', label: 'Weather', buttonId: 'btn-desktop-nav-projects' },
    { id: 'settings', label: 'Alerts', buttonId: 'btn-desktop-nav-settings' },
    { id: 'blueprints', label: 'Reports', buttonId: 'btn-desktop-nav-blueprints' },
  ];

  return (
    <nav
      className={cn(
        'hidden lg:flex items-center gap-1 bg-white/70 backdrop-blur-2xl p-1 rounded-full border border-white/85 shadow-[0_2px_12px_rgba(0,0,0,0.03),inset_0_1px_1px_rgba(255,255,255,0.9)]',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = currentTab === tab.id || (tab.id === 'home' && (currentTab === '' || currentTab === 'overview'));
        return (
          <button
            key={tab.id}
            id={tab.buttonId}
            onClick={() => {
              if (tab.onClick) {
                tab.onClick();
              } else {
                onTabChange(tab.id);
              }
            }}
            className={cn(
              'px-3.5 py-1.5 rounded-full text-xs font-bold transition-all select-none cursor-pointer',
              isActive
                ? 'bg-[#FFD21F] text-slate-950 shadow-xs'
                : 'text-slate-600 hover:text-slate-950 hover:bg-white/70'
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
};

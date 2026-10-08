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
  const tabs: Array<{ id: string; label: string; buttonId: string; onClick?: () => void }> = [
    { id: 'home', label: 'Overview', buttonId: 'btn-desktop-nav-home' },
    { id: 'site', label: 'Site Map', buttonId: 'btn-desktop-nav-site' },
    { id: 'weather', label: 'Weather', buttonId: 'btn-desktop-nav-weather' },
    { id: 'turbines', label: 'Turbines', buttonId: 'btn-desktop-nav-turbines' },
    { id: 'optimize', label: 'Optimization', buttonId: 'btn-desktop-nav-optimize' },
    { id: 'results', label: 'Results', buttonId: 'btn-desktop-nav-results' },
    { id: 'blueprints', label: 'Reports', buttonId: 'btn-desktop-nav-blueprints' },
  ];

  return (
    <nav
      className={cn(
        'hidden md:flex items-center gap-1 bg-white/70 backdrop-blur-2xl p-1 rounded-full border border-white/85 shadow-[0_2px_12px_rgba(0,0,0,0.03),inset_0_1px_1px_rgba(255,255,255,0.9)]',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive =
          currentTab === tab.id ||
          (tab.id === 'home' && (currentTab === '' || currentTab === 'overview' || currentTab === 'home' || currentTab === 'dashboard')) ||
          (tab.id === 'turbines' && (currentTab === 'config' || currentTab === 'turbines' || currentTab === 's2_config')) ||
          (tab.id === 'site' && (currentTab === 'map' || currentTab === 'site' || currentTab === 's1_site' || currentTab === 'new')) ||
          (tab.id === 'weather' && currentTab === 'weather') ||
          (tab.id === 'optimize' && (currentTab === 'analysis' || currentTab === 'optimize' || currentTab === 's3_analysis' || currentTab === 's4_optimize')) ||
          (tab.id === 'results' && (currentTab === 'inspect' || currentTab === 'results' || currentTab === 's5_inspect')) ||
          (tab.id === 'blueprints' && (currentTab === 'blueprints' || currentTab === 'reports' || currentTab === 's6_blueprint'));
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
              'px-3 py-1.5 rounded-full text-xs font-bold transition-all select-none cursor-pointer',
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

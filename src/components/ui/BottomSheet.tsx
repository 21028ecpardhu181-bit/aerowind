import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { GlassPanel } from './GlassPanel';
import { cn } from '../../lib/utils';

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  className,
}) => {
  // Prevent background scrolling when sheet is open on mobile
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end md:hidden">
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet Content with Liquid Glass Styling */}
      <GlassPanel
        variant="elevated"
        className={cn(
          'relative z-10 w-full max-h-[85vh] rounded-t-3xl border-b-0 border-x-0 overflow-hidden flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-300',
          className
        )}
      >
        {/* Grab Handle */}
        <div className="flex justify-center pt-3 pb-1" onClick={onClose}>
          <div className="w-12 h-1.5 rounded-full bg-slate-300 hover:bg-slate-400 cursor-pointer transition-colors" />
        </div>

        {/* Sheet Header */}
        {(title || subtitle) && (
          <div className="px-5 py-3 border-b border-slate-200/80 flex items-center justify-between">
            <div>
              {title && <h3 className="text-base font-bold text-slate-900">{title}</h3>}
              {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Sheet Body with Internal Scroll */}
        <div className="p-5 overflow-y-auto max-h-[calc(85vh-80px)]">
          {children}
        </div>
      </GlassPanel>
    </div>
  );
};

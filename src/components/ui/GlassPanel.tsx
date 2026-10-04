import React from 'react';
import { cn } from '../../lib/utils';

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'standard' | 'elevated' | 'subtle';
  children: React.ReactNode;
}

/**
 * GlassPanel — Apple-level Liquid Glass container with authentic specular rim lighting,
 * frosted backdrop diffusion, and subtle depth borders.
 */
export const GlassPanel = React.forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, variant = 'standard', children, ...props }, ref) => {
    const variantStyles = {
      standard: 'liquid-glass rounded-2xl md:rounded-3xl',
      elevated: 'liquid-glass-elevated rounded-2xl md:rounded-3xl',
      subtle: 'liquid-glass-subtle rounded-xl md:rounded-2xl',
    };

    return (
      <div
        ref={ref}
        className={cn(variantStyles[variant], 'transition-all duration-200', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

GlassPanel.displayName = 'GlassPanel';

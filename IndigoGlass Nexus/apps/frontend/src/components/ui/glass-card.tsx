// =============================================================================
// IndigoGlass Nexus - GlassCard Component
// =============================================================================

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const paddingClasses = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export function GlassCard({
  children,
  className,
  hover = true,
  padding = 'md',
}: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-2xl backdrop-blur-xl',
        'bg-white/10 border border-white/20',
        'shadow-[0_8px_32px_0_rgba(31,38,135,0.37)]',
        'transition-all duration-300',
        hover && 'hover:bg-white/15 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_0_rgba(31,38,135,0.45)]',
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  );
}

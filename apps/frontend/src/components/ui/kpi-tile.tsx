// =============================================================================
// IndigoGlass Nexus - KpiTile Component
// =============================================================================

import { cn } from '@/lib/utils';
import { GlassCard } from './glass-card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiTileProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label?: string;
  };
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
}

export function KpiTile({
  title,
  value,
  subtitle,
  trend,
  icon,
  loading = false,
  className,
}: KpiTileProps) {
  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) return <TrendingUp className="w-4 h-4" />;
    if (trend.value < 0) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) return 'text-emerald-400';
    if (trend.value < 0) return 'text-rose-400';
    return 'text-gray-400';
  };

  if (loading) {
    return (
      <GlassCard className={cn('min-h-[140px]', className)}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-white/10 rounded w-1/2" />
          <div className="h-8 bg-white/10 rounded w-3/4" />
          <div className="h-3 bg-white/10 rounded w-1/3" />
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className={cn('min-h-[140px] flex flex-col justify-between', className)}>
      <div className="flex items-start justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          {title}
        </span>
        {icon && (
          <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-2">
        <div className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
          {value}
        </div>
        {subtitle && (
          <p className="text-sm text-gray-400 mt-1">{subtitle}</p>
        )}
      </div>

      {trend && (
        <div className={cn('flex items-center gap-1 mt-3 text-sm', getTrendColor())}>
          {getTrendIcon()}
          <span className="font-medium">
            {trend.value > 0 ? '+' : ''}{trend.value}%
          </span>
          {trend.label && (
            <span className="text-gray-500 ml-1">{trend.label}</span>
          )}
        </div>
      )}
    </GlassCard>
  );
}

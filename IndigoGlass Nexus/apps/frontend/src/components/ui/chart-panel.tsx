// =============================================================================
// IndigoGlass Nexus - Chart Panel Component (Recharts wrapper with glass styling)
// =============================================================================

'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { GlassCard } from './glass-card';
import { MoreHorizontal, Maximize2, Download } from 'lucide-react';

interface ChartPanelProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  headerActions?: ReactNode;
  loading?: boolean;
  fullscreen?: boolean;
  onFullscreen?: () => void;
  onExport?: () => void;
}

export function ChartPanel({
  title,
  subtitle,
  children,
  className,
  headerActions,
  loading = false,
  fullscreen = false,
  onFullscreen,
  onExport,
}: ChartPanelProps) {
  return (
    <GlassCard className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>
          )}
        </div>
        
        <div className="flex items-center gap-1">
          {headerActions}
          
          {onExport && (
            <button
              onClick={onExport}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              title="Export chart"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
          
          {onFullscreen && (
            <button
              onClick={onFullscreen}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
              title="Fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          )}
          
          <button className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all">
            <MoreHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chart content */}
      <div className="flex-1 min-h-0 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <span className="text-sm text-gray-400">Loading chart...</span>
            </div>
          </div>
        ) : (
          children
        )}
      </div>
    </GlassCard>
  );
}

// Chart color palette for consistent styling
export const chartColors = {
  primary: '#6366f1', // Indigo
  secondary: '#8b5cf6', // Purple
  tertiary: '#06b6d4', // Cyan
  success: '#10b981', // Emerald
  warning: '#f59e0b', // Amber
  danger: '#ef4444', // Rose
  gray: '#6b7280',
  
  // Gradients for area charts
  gradients: {
    primary: ['rgba(99, 102, 241, 0.3)', 'rgba(99, 102, 241, 0)'],
    secondary: ['rgba(139, 92, 246, 0.3)', 'rgba(139, 92, 246, 0)'],
    success: ['rgba(16, 185, 129, 0.3)', 'rgba(16, 185, 129, 0)'],
  },
};

// Common chart config for glassmorphism styling
export const chartConfig = {
  xAxis: {
    stroke: 'rgba(255, 255, 255, 0.1)',
    tick: { fill: 'rgba(255, 255, 255, 0.5)', fontSize: 12 },
    axisLine: { stroke: 'rgba(255, 255, 255, 0.1)' },
  },
  yAxis: {
    stroke: 'rgba(255, 255, 255, 0.1)',
    tick: { fill: 'rgba(255, 255, 255, 0.5)', fontSize: 12 },
    axisLine: { stroke: 'rgba(255, 255, 255, 0.1)' },
  },
  grid: {
    stroke: 'rgba(255, 255, 255, 0.05)',
    strokeDasharray: '4 4',
  },
  tooltip: {
    contentStyle: {
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: '8px',
      backdropFilter: 'blur(10px)',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
    },
    labelStyle: { color: 'white', fontWeight: 500 },
    itemStyle: { color: 'rgba(255, 255, 255, 0.7)' },
  },
  legend: {
    wrapperStyle: { paddingTop: '16px' },
    iconType: 'circle' as const,
    formatter: (value: string) => (
      <span style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '12px' }}>{value}</span>
    ),
  },
};

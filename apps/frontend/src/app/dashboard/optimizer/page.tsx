// =============================================================================
// IndigoGlass Nexus - Route Optimizer Page
// =============================================================================

'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Truck, MapPin, Clock, DollarSign, Leaf, Play, RotateCcw } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { ChartPanel, chartColors, chartConfig } from '@/components/ui/chart-panel';
import { DataTable } from '@/components/ui/data-table';
import { optimizerApi } from '@/lib/api';
import { formatNumber, formatCurrency, cn } from '@/lib/utils';
import { useToaster } from '@/components/ui/toaster';

// Mock route data
const mockRoutes = [
  {
    id: 'R-001',
    vehicle: 'Truck-A1',
    stops: 8,
    distance: 245.6,
    duration: 6.5,
    cost: 890,
    co2: 45.2,
    utilization: 0.85,
  },
  {
    id: 'R-002',
    vehicle: 'Truck-A2',
    stops: 6,
    distance: 198.3,
    duration: 5.2,
    cost: 720,
    co2: 36.5,
    utilization: 0.72,
  },
  {
    id: 'R-003',
    vehicle: 'Truck-B1',
    stops: 10,
    distance: 312.8,
    duration: 8.1,
    cost: 1150,
    co2: 58.4,
    utilization: 0.92,
  },
  {
    id: 'R-004',
    vehicle: 'Truck-B2',
    stops: 7,
    distance: 178.5,
    duration: 4.8,
    cost: 650,
    co2: 32.8,
    utilization: 0.68,
  },
  {
    id: 'R-005',
    vehicle: 'Van-C1',
    stops: 12,
    distance: 145.2,
    duration: 5.5,
    cost: 420,
    co2: 21.3,
    utilization: 0.88,
  },
];

const mockComparisonData = [
  { metric: 'Total Distance', before: 1450, after: 1080, unit: 'km' },
  { metric: 'Total Time', before: 42, after: 30, unit: 'hrs' },
  { metric: 'Total Cost', before: 5200, after: 3830, unit: '$' },
  { metric: 'CO₂ Emissions', before: 268, after: 194, unit: 'kg' },
];

const mockVehicleUtilization = [
  { vehicle: 'Truck-A1', capacity: 1000, used: 850 },
  { vehicle: 'Truck-A2', capacity: 1000, used: 720 },
  { vehicle: 'Truck-B1', capacity: 1500, used: 1380 },
  { vehicle: 'Truck-B2', capacity: 1500, used: 1020 },
  { vehicle: 'Van-C1', capacity: 500, used: 440 },
];

export default function OptimizerPage() {
  const toaster = useToaster();
  const [isOptimizing, setIsOptimizing] = useState(false);

  const handleOptimize = async () => {
    setIsOptimizing(true);
    // Simulate optimization
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsOptimizing(false);
    toaster.success('Optimization Complete', 'Routes have been optimized successfully');
  };

  const totalSavings = mockComparisonData.reduce((acc, item) => {
    if (item.unit === '$') {
      return acc + (item.before - item.after);
    }
    return acc;
  }, 0);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Route Optimizer</h1>
          <p className="text-gray-400 mt-1">
            AI-powered vehicle routing with OR-Tools
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleOptimize}
            disabled={isOptimizing}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
              isOptimizing
                ? 'bg-indigo-500/50 text-white/70 cursor-not-allowed'
                : 'bg-indigo-500 text-white hover:bg-indigo-600'
            )}
          >
            {isOptimizing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Optimizing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Optimization
              </>
            )}
          </button>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KpiTile
          title="Active Routes"
          value="5"
          trend={0}
        />
        <KpiTile
          title="Total Distance"
          value="1,080 km"
          trend={-25.5}
        />
        <KpiTile
          title="Cost Savings"
          value={formatCurrency(totalSavings)}
          trend={26.4}
        />
        <KpiTile
          title="CO₂ Reduced"
          value="74 kg"
          trend={-27.6}
        />
        <KpiTile
          title="Avg Utilization"
          value="81%"
          trend={12.3}
        />
      </div>

      {/* Map placeholder + comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map placeholder */}
        <GlassCard className="lg:col-span-2 h-[400px] flex flex-col">
          <h3 className="font-semibold text-white mb-4">Route Map</h3>
          <div className="flex-1 rounded-lg bg-gray-800/50 border border-white/10 flex items-center justify-center">
            <div className="text-center">
              <MapPin className="w-12 h-12 text-indigo-400 mx-auto mb-3 opacity-50" />
              <p className="text-gray-400">Interactive map with MapLibre GL</p>
              <p className="text-gray-500 text-sm mt-1">Routes visualized with color-coded paths</p>
            </div>
          </div>
        </GlassCard>

        {/* Before/After comparison */}
        <GlassCard className="h-[400px]">
          <h3 className="font-semibold text-white mb-4">Optimization Impact</h3>
          <div className="space-y-4">
            {mockComparisonData.map((item) => {
              const improvement = ((item.before - item.after) / item.before) * 100;
              return (
                <div key={item.metric} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">{item.metric}</span>
                    <span className="text-emerald-400">-{improvement.toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 mb-1">Before</div>
                      <div className="h-2 bg-rose-500/30 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-rose-500 rounded-full"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {formatNumber(item.before)} {item.unit}
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="text-xs text-gray-500 mb-1">After</div>
                      <div className="h-2 bg-emerald-500/30 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${(item.after / item.before) * 100}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {formatNumber(item.after)} {item.unit}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>

      {/* Vehicle utilization + Routes table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vehicle utilization */}
        <ChartPanel
          title="Vehicle Utilization"
          subtitle="Capacity usage by vehicle"
          className="h-[320px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockVehicleUtilization} layout="vertical">
              <CartesianGrid {...chartConfig.grid} />
              <XAxis type="number" {...chartConfig.xAxis} />
              <YAxis type="category" dataKey="vehicle" {...chartConfig.yAxis} width={80} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Bar dataKey="used" fill={chartColors.primary} name="Used" radius={[0, 4, 4, 0]} />
              <Bar dataKey="capacity" fill={chartColors.gray} name="Capacity" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Routes table */}
        <GlassCard className="h-[320px] overflow-hidden">
          <h3 className="font-semibold text-white mb-4">Optimized Routes</h3>
          <div className="overflow-auto h-[calc(100%-36px)]">
            <DataTable
              data={mockRoutes}
              columns={[
                {
                  key: 'id',
                  header: 'Route',
                  sortable: true,
                  className: 'font-mono text-indigo-400',
                },
                {
                  key: 'stops',
                  header: 'Stops',
                  sortable: true,
                },
                {
                  key: 'distance',
                  header: 'Distance',
                  sortable: true,
                  accessor: (row) => `${(row.distance as number).toFixed(1)} km`,
                },
                {
                  key: 'duration',
                  header: 'Time',
                  sortable: true,
                  accessor: (row) => `${(row.duration as number).toFixed(1)} hrs`,
                },
                {
                  key: 'cost',
                  header: 'Cost',
                  sortable: true,
                  accessor: (row) => formatCurrency(row.cost as number),
                },
                {
                  key: 'utilization',
                  header: 'Util.',
                  sortable: true,
                  accessor: (row) => {
                    const util = row.utilization as number;
                    return (
                      <span className={cn(
                        util >= 0.85 ? 'text-emerald-400' :
                        util >= 0.70 ? 'text-amber-400' : 'text-rose-400'
                      )}>
                        {(util * 100).toFixed(0)}%
                      </span>
                    );
                  },
                },
              ]}
              searchable={false}
              pageSize={5}
            />
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

// =============================================================================
// IndigoGlass Nexus - Sustainability Page
// =============================================================================

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Leaf, TrendingDown, Truck, Factory, Recycle, Droplets } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { ChartPanel, chartColors, chartConfig } from '@/components/ui/chart-panel';
import { DataTable } from '@/components/ui/data-table';
import { sustainabilityApi } from '@/lib/api';
import { formatNumber, formatPercent } from '@/lib/utils';

// Mock data
const mockEmissionsTrend = [
  { month: 'Jan', transport: 450, warehouse: 120, production: 280 },
  { month: 'Feb', transport: 420, warehouse: 115, production: 275 },
  { month: 'Mar', transport: 380, warehouse: 110, production: 260 },
  { month: 'Apr', transport: 390, warehouse: 105, production: 250 },
  { month: 'May', transport: 350, warehouse: 100, production: 240 },
  { month: 'Jun', transport: 320, warehouse: 95, production: 230 },
];

const mockEmissionsBySource = [
  { name: 'Transport', value: 320, color: chartColors.primary },
  { name: 'Warehouse', value: 95, color: chartColors.secondary },
  { name: 'Production', value: 230, color: chartColors.tertiary },
  { name: 'Other', value: 55, color: chartColors.gray },
];

const mockTargetProgress = [
  { category: 'Carbon Neutral', target: 100, current: 68, deadline: '2030' },
  { category: 'Renewable Energy', target: 100, current: 45, deadline: '2028' },
  { category: 'Zero Waste', target: 100, current: 72, deadline: '2027' },
  { category: 'Water Reduction', target: 50, current: 35, deadline: '2026' },
];

const mockLocationEmissions = [
  { location: 'Warehouse A', emissions: 125, target: 100, status: 'over' },
  { location: 'Warehouse B', emissions: 85, target: 100, status: 'good' },
  { location: 'DC North', emissions: 95, target: 100, status: 'good' },
  { location: 'DC South', emissions: 78, target: 100, status: 'good' },
  { location: 'DC East', emissions: 110, target: 100, status: 'over' },
  { location: 'Fleet Operations', emissions: 320, target: 350, status: 'good' },
];

export default function SustainabilityPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('6m');

  const totalEmissions = mockEmissionsBySource.reduce((acc, item) => acc + item.value, 0);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sustainability</h1>
          <p className="text-gray-400 mt-1">
            Environmental impact tracking and ESG metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50"
          >
            <option value="1m">Last Month</option>
            <option value="3m">Last 3 Months</option>
            <option value="6m">Last 6 Months</option>
            <option value="1y">Last Year</option>
          </select>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KpiTile
          title="Total CO₂"
          value={`${formatNumber(totalEmissions)} t`}
          trend={-15.2}
        />
        <KpiTile
          title="vs Target"
          value="-8.5%"
          trend={12.0}
        />
        <KpiTile
          title="Renewable %"
          value="45%"
          trend={8.3}
        />
        <KpiTile
          title="Waste Diverted"
          value="72%"
          trend={5.1}
        />
        <KpiTile
          title="Water Saved"
          value="1.2M gal"
          trend={22.5}
        />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Emissions trend */}
        <ChartPanel
          title="Emissions Trend"
          subtitle="By source category"
          className="lg:col-span-2 h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={mockEmissionsTrend}>
              <defs>
                <linearGradient id="colorTransport" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorWarehouse" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.secondary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColors.secondary} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorProduction" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.tertiary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColors.tertiary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...chartConfig.grid} />
              <XAxis dataKey="month" {...chartConfig.xAxis} />
              <YAxis {...chartConfig.yAxis} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Area
                type="monotone"
                dataKey="transport"
                stackId="1"
                stroke={chartColors.primary}
                fill="url(#colorTransport)"
                name="Transport"
              />
              <Area
                type="monotone"
                dataKey="warehouse"
                stackId="1"
                stroke={chartColors.secondary}
                fill="url(#colorWarehouse)"
                name="Warehouse"
              />
              <Area
                type="monotone"
                dataKey="production"
                stackId="1"
                stroke={chartColors.tertiary}
                fill="url(#colorProduction)"
                name="Production"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Emissions by source pie */}
        <ChartPanel
          title="Emissions by Source"
          subtitle="Current period breakdown"
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mockEmissionsBySource}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {mockEmissionsBySource.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      {/* Target progress */}
      <GlassCard>
        <h3 className="font-semibold text-white mb-6">Sustainability Targets</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {mockTargetProgress.map((target) => {
            const progress = (target.current / target.target) * 100;
            const isOnTrack = progress >= 50;
            
            return (
              <div key={target.category} className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-white">{target.category}</span>
                  <span className="text-xs text-gray-500">Target: {target.deadline}</span>
                </div>
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isOnTrack ? 'bg-emerald-500' : 'bg-amber-500'
                    }`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className={isOnTrack ? 'text-emerald-400' : 'text-amber-400'}>
                    {target.current}%
                  </span>
                  <span className="text-gray-500">of {target.target}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </GlassCard>

      {/* Location emissions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPanel
          title="Emissions by Location"
          subtitle="Monthly CO₂ (tonnes)"
          className="h-[320px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockLocationEmissions} layout="vertical">
              <CartesianGrid {...chartConfig.grid} />
              <XAxis type="number" {...chartConfig.xAxis} />
              <YAxis type="category" dataKey="location" {...chartConfig.yAxis} width={120} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Bar dataKey="emissions" name="Actual" radius={[0, 4, 4, 0]}>
                {mockLocationEmissions.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.status === 'good' ? chartColors.success : chartColors.warning}
                  />
                ))}
              </Bar>
              <Bar dataKey="target" fill={chartColors.gray} name="Target" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Quick facts */}
        <GlassCard className="h-[320px]">
          <h3 className="font-semibold text-white mb-4">Environmental Impact</h3>
          <div className="space-y-4">
            {[
              {
                icon: Truck,
                label: 'Fleet Efficiency',
                value: '+18% MPG',
                detail: 'Average fuel economy improvement',
                color: 'text-indigo-400',
              },
              {
                icon: Factory,
                label: 'Clean Energy',
                value: '45% Renewable',
                detail: 'Of total energy consumption',
                color: 'text-purple-400',
              },
              {
                icon: Recycle,
                label: 'Waste Recycled',
                value: '1,250 tonnes',
                detail: 'Materials diverted from landfill',
                color: 'text-emerald-400',
              },
              {
                icon: Droplets,
                label: 'Water Conservation',
                value: '1.2M gallons',
                detail: 'Saved through process improvements',
                color: 'text-cyan-400',
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center gap-4 p-3 rounded-lg bg-white/5"
              >
                <div className={`p-2 rounded-lg bg-white/10 ${item.color}`}>
                  <item.icon className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">{item.label}</span>
                    <span className="font-medium text-white">{item.value}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
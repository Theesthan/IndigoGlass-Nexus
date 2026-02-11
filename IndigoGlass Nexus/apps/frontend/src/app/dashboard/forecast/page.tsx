// =============================================================================
// IndigoGlass Nexus - Forecast Page
// =============================================================================

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, Target, Calendar, ArrowRight } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { ChartPanel, chartColors, chartConfig } from '@/components/ui/chart-panel';
import { DataTable } from '@/components/ui/data-table';
import { forecastApi } from '@/lib/api';
import { formatNumber, formatPercent, formatCurrency } from '@/lib/utils';

// Mock forecast data
const mockForecastData = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() + i);
  const base = 1000 + Math.sin(i * 0.3) * 200;
  return {
    date: date.toISOString().split('T')[0],
    forecast: Math.round(base + Math.random() * 100),
    lower: Math.round(base - 150 - Math.random() * 50),
    upper: Math.round(base + 250 + Math.random() * 50),
    actual: i < 7 ? Math.round(base + (Math.random() - 0.5) * 150) : null,
  };
});

const mockAccuracyData = [
  { month: 'Jan', mape: 0.082, bias: -0.02 },
  { month: 'Feb', mape: 0.075, bias: 0.01 },
  { month: 'Mar', mape: 0.068, bias: -0.005 },
  { month: 'Apr', mape: 0.091, bias: -0.03 },
  { month: 'May', mape: 0.063, bias: 0.015 },
  { month: 'Jun', mape: 0.055, bias: 0.008 },
];

const mockProductForecasts = [
  { sku: 'SKU-001', product: 'Paracetamol 500mg', forecast: 15200, confidence: 0.92, trend: 'up' },
  { sku: 'SKU-002', product: 'Ibuprofen 200mg', forecast: 12800, confidence: 0.88, trend: 'stable' },
  { sku: 'SKU-003', product: 'Vitamin C 1000mg', forecast: 9500, confidence: 0.95, trend: 'up' },
  { sku: 'SKU-004', product: 'Aspirin 100mg', forecast: 8200, confidence: 0.85, trend: 'down' },
  { sku: 'SKU-005', product: 'Omeprazole 20mg', forecast: 6700, confidence: 0.91, trend: 'stable' },
  { sku: 'SKU-006', product: 'Metformin 500mg', forecast: 5900, confidence: 0.87, trend: 'up' },
  { sku: 'SKU-007', product: 'Atorvastatin 10mg', forecast: 5200, confidence: 0.89, trend: 'down' },
];

export default function ForecastPage() {
  const [selectedHorizon, setSelectedHorizon] = useState('30');
  const [selectedModel, setSelectedModel] = useState('xgboost');

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Demand Forecast</h1>
          <p className="text-gray-400 mt-1">
            AI-powered demand predictions and accuracy metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50"
          >
            <option value="xgboost">XGBoost Model</option>
            <option value="prophet">Prophet Model</option>
            <option value="ensemble">Ensemble</option>
          </select>
          <select
            value={selectedHorizon}
            onChange={(e) => setSelectedHorizon(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50"
          >
            <option value="7">7 days</option>
            <option value="14">14 days</option>
            <option value="30">30 days</option>
            <option value="90">90 days</option>
          </select>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiTile
          title="Forecast Accuracy"
          value="94.5%"
          trend={2.3}
        />
        <KpiTile
          title="MAPE"
          value="5.5%"
          trend={-8.2}
        />
        <KpiTile
          title="Forecast Bias"
          value="+0.8%"
          trend={-15.0}
        />
        <KpiTile
          title="Active Models"
          value="3"
          trend={0}
        />
      </div>

      {/* Main forecast chart */}
      <ChartPanel
        title="30-Day Demand Forecast"
        subtitle="With 95% confidence interval"
        className="h-[400px]"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={mockForecastData}>
            <defs>
              <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={chartColors.primary} stopOpacity={0.1} />
                <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid {...chartConfig.grid} />
            <XAxis dataKey="date" {...chartConfig.xAxis} />
            <YAxis {...chartConfig.yAxis} />
            <Tooltip {...chartConfig.tooltip} />
            <Legend {...chartConfig.legend} />
            
            {/* Confidence interval */}
            <Area
              type="monotone"
              dataKey="upper"
              stroke="transparent"
              fill="url(#colorConfidence)"
              name="Upper Bound"
            />
            <Area
              type="monotone"
              dataKey="lower"
              stroke="transparent"
              fill="transparent"
              name="Lower Bound"
            />
            
            {/* Forecast line */}
            <Line
              type="monotone"
              dataKey="forecast"
              stroke={chartColors.primary}
              strokeWidth={2}
              dot={false}
              name="Forecast"
            />
            
            {/* Actual data */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke={chartColors.success}
              strokeWidth={2}
              dot={{ fill: chartColors.success, r: 3 }}
              name="Actual"
            />
            
            {/* Today marker */}
            <ReferenceLine
              x={mockForecastData[6].date}
              stroke="rgba(255, 255, 255, 0.3)"
              strokeDasharray="3 3"
              label={{
                value: 'Today',
                fill: 'rgba(255, 255, 255, 0.5)',
                fontSize: 12,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartPanel>

      {/* Accuracy trend + Product forecasts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy trend */}
        <ChartPanel
          title="Forecast Accuracy Trend"
          subtitle="MAPE by month"
          className="h-[320px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockAccuracyData}>
              <CartesianGrid {...chartConfig.grid} />
              <XAxis dataKey="month" {...chartConfig.xAxis} />
              <YAxis {...chartConfig.yAxis} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip
                {...chartConfig.tooltip}
                formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
              />
              <Legend {...chartConfig.legend} />
              <Line
                type="monotone"
                dataKey="mape"
                stroke={chartColors.primary}
                strokeWidth={2}
                name="MAPE"
                dot={{ fill: chartColors.primary, r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="bias"
                stroke={chartColors.warning}
                strokeWidth={2}
                name="Bias"
                dot={{ fill: chartColors.warning, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Product forecasts table */}
        <GlassCard className="h-[320px] overflow-hidden">
          <h3 className="font-semibold text-white mb-4">Top Product Forecasts</h3>
          <div className="overflow-auto h-[calc(100%-36px)]">
            <DataTable
              data={mockProductForecasts}
              columns={[
                {
                  key: 'sku',
                  header: 'SKU',
                  sortable: true,
                  className: 'font-mono text-indigo-400',
                },
                {
                  key: 'product',
                  header: 'Product',
                  sortable: true,
                },
                {
                  key: 'forecast',
                  header: 'Next 30d',
                  sortable: true,
                  accessor: (row) => formatNumber(row.forecast as number),
                },
                {
                  key: 'confidence',
                  header: 'Conf.',
                  sortable: true,
                  accessor: (row) => (
                    <span className={
                      (row.confidence as number) >= 0.9 ? 'text-emerald-400' :
                      (row.confidence as number) >= 0.85 ? 'text-amber-400' : 'text-rose-400'
                    }>
                      {formatPercent(row.confidence as number)}
                    </span>
                  ),
                },
                {
                  key: 'trend',
                  header: 'Trend',
                  accessor: (row) => (
                    <span className={
                      row.trend === 'up' ? 'text-emerald-400' :
                      row.trend === 'down' ? 'text-rose-400' : 'text-gray-400'
                    }>
                      {row.trend === 'up' ? '↑' : row.trend === 'down' ? '↓' : '→'}
                    </span>
                  ),
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

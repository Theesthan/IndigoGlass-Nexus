// =============================================================================
// IndigoGlass Nexus - Dashboard Overview Page
// =============================================================================

'use client';

import { useMemo } from 'react';
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
import {
  TrendingUp,
  Package,
  Truck,
  Leaf,
  AlertTriangle,
  DollarSign,
  Target,
} from 'lucide-react';
import { KpiTile } from '@/components/ui/kpi-tile';
import { ChartPanel, chartColors, chartConfig } from '@/components/ui/chart-panel';
import { GlassCard } from '@/components/ui/glass-card';
import { kpiApi, forecastApi, inventoryApi, sustainabilityApi } from '@/lib/api';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils';

// Mock data for demonstration
const mockTrendData = [
  { date: '2024-01', actual: 2400, forecast: 2200, baseline: 2000 },
  { date: '2024-02', actual: 2210, forecast: 2350, baseline: 2100 },
  { date: '2024-03', actual: 2290, forecast: 2400, baseline: 2150 },
  { date: '2024-04', actual: 2000, forecast: 2100, baseline: 2050 },
  { date: '2024-05', actual: 2181, forecast: 2200, baseline: 2100 },
  { date: '2024-06', actual: 2500, forecast: 2450, baseline: 2200 },
  { date: '2024-07', actual: 2100, forecast: 2300, baseline: 2150 },
];

const mockCategoryData = [
  { name: 'Pharma', value: 45 },
  { name: 'Consumer', value: 30 },
  { name: 'Medical', value: 15 },
  { name: 'Other', value: 10 },
];

const mockInventoryRisk = [
  { location: 'Warehouse A', overstock: 15, understock: 5, optimal: 80 },
  { location: 'Warehouse B', overstock: 8, understock: 12, optimal: 80 },
  { location: 'DC North', overstock: 20, understock: 3, optimal: 77 },
  { location: 'DC South', overstock: 5, understock: 18, optimal: 77 },
  { location: 'DC East', overstock: 10, understock: 8, optimal: 82 },
];

export default function DashboardPage() {
  // Fetch KPIs
  const { data: kpiSnapshot, isLoading: kpiLoading } = useQuery({
    queryKey: ['kpis', 'snapshot'],
    queryFn: kpiApi.getSnapshot,
    staleTime: 60000,
    // Use mock data for now
    placeholderData: {
      generated_at: new Date().toISOString(),
      metrics: {
        total_revenue: 12450000,
        revenue_trend: 8.5,
        total_units_sold: 245000,
        units_trend: 5.2,
        forecast_accuracy: 0.923,
        accuracy_trend: 2.1,
        inventory_value: 8200000,
        inventory_trend: -3.2,
        co2_emissions: 1250,
        emissions_trend: -12.5,
        on_time_delivery: 0.945,
        delivery_trend: 1.8,
        stockout_rate: 0.032,
        stockout_trend: -15.0,
        orders_pending: 342,
      },
    },
  });

  const kpis = useMemo(() => {
    if (!kpiSnapshot?.metrics) return [];
    const m = kpiSnapshot.metrics;
    return [
      {
        title: 'Revenue',
        value: formatCurrency(m.total_revenue),
        trend: m.revenue_trend || 0,
        icon: DollarSign,
        color: 'indigo' as const,
      },
      {
        title: 'Forecast Accuracy',
        value: formatPercent(m.forecast_accuracy),
        trend: m.accuracy_trend || 0,
        icon: Target,
        color: 'emerald' as const,
      },
      {
        title: 'Inventory Value',
        value: formatCurrency(m.inventory_value),
        trend: m.inventory_trend || 0,
        icon: Package,
        color: 'purple' as const,
      },
      {
        title: 'CO₂ Emissions',
        value: `${formatNumber(m.co2_emissions)} t`,
        trend: m.emissions_trend || 0,
        icon: Leaf,
        color: 'emerald' as const,
        invertTrend: true,
      },
      {
        title: 'On-Time Delivery',
        value: formatPercent(m.on_time_delivery),
        trend: m.delivery_trend || 0,
        icon: Truck,
        color: 'cyan' as const,
      },
      {
        title: 'Stockout Rate',
        value: formatPercent(m.stockout_rate),
        trend: m.stockout_trend || 0,
        icon: AlertTriangle,
        color: 'rose' as const,
        invertTrend: true,
      },
    ];
  }, [kpiSnapshot]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard Overview</h1>
          <p className="text-gray-400 mt-1">
            Supply chain analytics and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50">
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((kpi, index) => (
          <KpiTile
            key={kpi.title}
            title={kpi.title}
            value={kpi.value}
            trend={kpi.trend}
            loading={kpiLoading}
          />
        ))}
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Demand trend chart */}
        <ChartPanel
          title="Demand Trend"
          subtitle="Actual vs Forecast"
          className="lg:col-span-2 h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={mockTrendData}>
              <defs>
                <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.secondary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColors.secondary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid {...chartConfig.grid} />
              <XAxis dataKey="date" {...chartConfig.xAxis} />
              <YAxis {...chartConfig.yAxis} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Area
                type="monotone"
                dataKey="actual"
                stroke={chartColors.primary}
                fill="url(#colorActual)"
                name="Actual"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="forecast"
                stroke={chartColors.secondary}
                fill="url(#colorForecast)"
                name="Forecast"
                strokeWidth={2}
                strokeDasharray="5 5"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Category distribution */}
        <ChartPanel
          title="Revenue by Category"
          subtitle="Current period"
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mockCategoryData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {mockCategoryData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={[chartColors.primary, chartColors.secondary, chartColors.tertiary, chartColors.gray][index]}
                  />
                ))}
              </Pie>
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Inventory risk by location */}
        <ChartPanel
          title="Inventory Risk by Location"
          subtitle="Stock level distribution"
          className="h-[320px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockInventoryRisk} layout="vertical">
              <CartesianGrid {...chartConfig.grid} />
              <XAxis type="number" {...chartConfig.xAxis} />
              <YAxis type="category" dataKey="location" {...chartConfig.yAxis} width={100} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Bar dataKey="optimal" stackId="a" fill={chartColors.success} name="Optimal" />
              <Bar dataKey="overstock" stackId="a" fill={chartColors.warning} name="Overstock" />
              <Bar dataKey="understock" stackId="a" fill={chartColors.danger} name="Understock" />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Quick actions / alerts */}
        <GlassCard className="h-[320px]">
          <h3 className="font-semibold text-white mb-4">Recent Alerts</h3>
          <div className="space-y-3">
            {[
              {
                type: 'warning',
                title: 'Low stock alert',
                message: 'SKU-12345 below reorder point at DC North',
                time: '5 min ago',
              },
              {
                type: 'info',
                title: 'Forecast updated',
                message: 'Q2 demand forecast recalculated with 94.2% accuracy',
                time: '1 hour ago',
              },
              {
                type: 'success',
                title: 'Route optimized',
                message: 'Fleet route optimization saved $2,450 in delivery costs',
                time: '3 hours ago',
              },
              {
                type: 'warning',
                title: 'Supplier delay',
                message: 'Shipment from Supplier A delayed by 2 days',
                time: '5 hours ago',
              },
            ].map((alert, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
              >
                <div
                  className={`w-2 h-2 rounded-full mt-2 ${
                    alert.type === 'warning'
                      ? 'bg-amber-500'
                      : alert.type === 'info'
                      ? 'bg-indigo-500'
                      : 'bg-emerald-500'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{alert.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{alert.message}</p>
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap">{alert.time}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

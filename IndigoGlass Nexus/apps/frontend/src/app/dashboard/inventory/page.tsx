// =============================================================================
// IndigoGlass Nexus - Inventory Page
// =============================================================================

'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell,
} from 'recharts';
import { Package, AlertTriangle, TrendingDown, TrendingUp, Warehouse } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { ChartPanel, chartColors, chartConfig } from '@/components/ui/chart-panel';
import { DataTable } from '@/components/ui/data-table';
import { inventoryApi } from '@/lib/api';
import { formatNumber, formatCurrency, cn } from '@/lib/utils';

// Mock inventory data
const mockInventoryByLocation = [
  { location: 'Warehouse A', current: 45000, optimal: 50000, safety: 10000 },
  { location: 'Warehouse B', current: 38000, optimal: 35000, safety: 8000 },
  { location: 'DC North', current: 22000, optimal: 25000, safety: 5000 },
  { location: 'DC South', current: 18000, optimal: 20000, safety: 4000 },
  { location: 'DC East', current: 28000, optimal: 30000, safety: 6000 },
  { location: 'DC West', current: 15000, optimal: 18000, safety: 4000 },
];

const mockRiskMatrix = [
  { sku: 'SKU-001', daysOfStock: 45, demandVariability: 0.15, value: 50000, risk: 'low' },
  { sku: 'SKU-002', daysOfStock: 8, demandVariability: 0.35, value: 75000, risk: 'high' },
  { sku: 'SKU-003', daysOfStock: 25, demandVariability: 0.20, value: 30000, risk: 'medium' },
  { sku: 'SKU-004', daysOfStock: 60, demandVariability: 0.10, value: 20000, risk: 'overstock' },
  { sku: 'SKU-005', daysOfStock: 5, demandVariability: 0.45, value: 100000, risk: 'critical' },
  { sku: 'SKU-006', daysOfStock: 30, demandVariability: 0.25, value: 45000, risk: 'low' },
  { sku: 'SKU-007', daysOfStock: 12, demandVariability: 0.30, value: 60000, risk: 'medium' },
  { sku: 'SKU-008', daysOfStock: 55, demandVariability: 0.08, value: 15000, risk: 'overstock' },
];

const mockInventoryItems = [
  { sku: 'SKU-001', product: 'Paracetamol 500mg', location: 'Warehouse A', quantity: 15000, reorderPoint: 5000, status: 'optimal' },
  { sku: 'SKU-002', product: 'Ibuprofen 200mg', location: 'Warehouse A', quantity: 2500, reorderPoint: 4000, status: 'low' },
  { sku: 'SKU-003', product: 'Vitamin C 1000mg', location: 'Warehouse B', quantity: 18000, reorderPoint: 6000, status: 'optimal' },
  { sku: 'SKU-004', product: 'Aspirin 100mg', location: 'DC North', quantity: 800, reorderPoint: 2000, status: 'critical' },
  { sku: 'SKU-005', product: 'Omeprazole 20mg', location: 'DC South', quantity: 25000, reorderPoint: 8000, status: 'overstock' },
  { sku: 'SKU-006', product: 'Metformin 500mg', location: 'DC East', quantity: 7500, reorderPoint: 3000, status: 'optimal' },
  { sku: 'SKU-007', product: 'Atorvastatin 10mg', location: 'DC West', quantity: 3200, reorderPoint: 4500, status: 'low' },
  { sku: 'SKU-008', product: 'Lisinopril 5mg', location: 'Warehouse A', quantity: 12000, reorderPoint: 5000, status: 'optimal' },
];

const riskColors: Record<string, string> = {
  low: chartColors.success,
  medium: chartColors.warning,
  high: chartColors.danger,
  critical: '#dc2626',
  overstock: chartColors.tertiary,
};

const statusStyles: Record<string, string> = {
  optimal: 'bg-emerald-500/20 text-emerald-400',
  low: 'bg-amber-500/20 text-amber-400',
  critical: 'bg-rose-500/20 text-rose-400',
  overstock: 'bg-cyan-500/20 text-cyan-400',
};

export default function InventoryPage() {
  const [selectedLocation, setSelectedLocation] = useState('all');

  const filteredItems = useMemo(() => {
    if (selectedLocation === 'all') return mockInventoryItems;
    return mockInventoryItems.filter(item => item.location === selectedLocation);
  }, [selectedLocation]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Inventory Management</h1>
          <p className="text-gray-400 mt-1">
            Real-time stock levels and risk analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Locations</option>
            <option value="Warehouse A">Warehouse A</option>
            <option value="Warehouse B">Warehouse B</option>
            <option value="DC North">DC North</option>
            <option value="DC South">DC South</option>
            <option value="DC East">DC East</option>
            <option value="DC West">DC West</option>
          </select>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KpiTile
          title="Total Units"
          value="166,000"
          trend={3.2}
        />
        <KpiTile
          title="Inventory Value"
          value="$8.2M"
          trend={-2.1}
        />
        <KpiTile
          title="Stockout Risk"
          value="3 SKUs"
          trend={-25.0}
        />
        <KpiTile
          title="Overstock Items"
          value="2 SKUs"
          trend={0}
        />
        <KpiTile
          title="Turn Rate"
          value="4.2x"
          trend={8.5}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Inventory by location */}
        <ChartPanel
          title="Stock Levels by Location"
          subtitle="Current vs optimal inventory"
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={mockInventoryByLocation}>
              <CartesianGrid {...chartConfig.grid} />
              <XAxis dataKey="location" {...chartConfig.xAxis} />
              <YAxis {...chartConfig.yAxis} tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} />
              <Tooltip {...chartConfig.tooltip} />
              <Legend {...chartConfig.legend} />
              <Bar dataKey="current" fill={chartColors.primary} name="Current" radius={[4, 4, 0, 0]} />
              <Bar dataKey="optimal" fill={chartColors.gray} name="Optimal" radius={[4, 4, 0, 0]} />
              <Bar dataKey="safety" fill={chartColors.warning} name="Safety Stock" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        {/* Risk matrix scatter */}
        <ChartPanel
          title="Inventory Risk Matrix"
          subtitle="Days of stock vs demand variability"
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid {...chartConfig.grid} />
              <XAxis
                type="number"
                dataKey="daysOfStock"
                name="Days of Stock"
                {...chartConfig.xAxis}
                label={{ value: 'Days of Stock', position: 'bottom', fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="demandVariability"
                name="Demand Variability"
                {...chartConfig.yAxis}
                tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                label={{ value: 'Variability', angle: -90, position: 'left', fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
              />
              <ZAxis type="number" dataKey="value" range={[50, 400]} name="Value" />
              <Tooltip
                {...chartConfig.tooltip}
                formatter={(value: number, name: string) => {
                  if (name === 'Demand Variability') return `${(value * 100).toFixed(1)}%`;
                  if (name === 'Value') return formatCurrency(value);
                  return value;
                }}
              />
              <Scatter name="SKUs" data={mockRiskMatrix}>
                {mockRiskMatrix.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={riskColors[entry.risk]} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      {/* Inventory table */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white">Inventory Items</h3>
          <div className="flex gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-emerald-500/20 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Optimal
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              Low
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-rose-500/20 text-rose-400">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              Critical
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-cyan-500/20 text-cyan-400">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              Overstock
            </span>
          </div>
        </div>
        <DataTable
          data={filteredItems}
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
              key: 'location',
              header: 'Location',
              sortable: true,
            },
            {
              key: 'quantity',
              header: 'Quantity',
              sortable: true,
              accessor: (row) => formatNumber(row.quantity as number),
            },
            {
              key: 'reorderPoint',
              header: 'Reorder Point',
              sortable: true,
              accessor: (row) => formatNumber(row.reorderPoint as number),
            },
            {
              key: 'status',
              header: 'Status',
              sortable: true,
              accessor: (row) => (
                <span className={cn('px-2 py-1 rounded text-xs capitalize', statusStyles[row.status as string])}>
                  {row.status as string}
                </span>
              ),
            },
          ]}
          pageSize={10}
          searchPlaceholder="Search products..."
        />
      </GlassCard>
    </div>
  );
}

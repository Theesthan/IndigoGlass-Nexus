// =============================================================================
// IndigoGlass Nexus - Supply Chain Lineage Page
// =============================================================================

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitBranch, Package, Truck, Factory, Store, Search, ZoomIn, ZoomOut } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { DataTable } from '@/components/ui/data-table';
import { graphApi } from '@/lib/api';
import { cn } from '@/lib/utils';

// Mock graph data
const mockNodes = [
  { id: 'SUP-001', type: 'supplier', name: 'PharmaChem Ltd', tier: 1 },
  { id: 'SUP-002', type: 'supplier', name: 'BioActive Inc', tier: 1 },
  { id: 'SUP-003', type: 'supplier', name: 'MedSupply Co', tier: 2 },
  { id: 'FAC-001', type: 'factory', name: 'Production Plant A', tier: 0 },
  { id: 'WH-001', type: 'warehouse', name: 'Central Warehouse', tier: 0 },
  { id: 'DC-001', type: 'dc', name: 'DC North', tier: 0 },
  { id: 'DC-002', type: 'dc', name: 'DC South', tier: 0 },
  { id: 'RET-001', type: 'retailer', name: 'PharmaMart', tier: -1 },
  { id: 'RET-002', type: 'retailer', name: 'HealthPlus', tier: -1 },
];

const mockEdges = [
  { source: 'SUP-001', target: 'FAC-001', leadTime: 5, reliability: 0.95 },
  { source: 'SUP-002', target: 'FAC-001', leadTime: 7, reliability: 0.88 },
  { source: 'SUP-003', target: 'SUP-001', leadTime: 14, reliability: 0.92 },
  { source: 'FAC-001', target: 'WH-001', leadTime: 2, reliability: 0.99 },
  { source: 'WH-001', target: 'DC-001', leadTime: 3, reliability: 0.97 },
  { source: 'WH-001', target: 'DC-002', leadTime: 4, reliability: 0.96 },
  { source: 'DC-001', target: 'RET-001', leadTime: 1, reliability: 0.98 },
  { source: 'DC-002', target: 'RET-002', leadTime: 1, reliability: 0.97 },
];

const mockPathways = [
  {
    id: 'PATH-001',
    product: 'Paracetamol 500mg',
    path: ['SUP-003', 'SUP-001', 'FAC-001', 'WH-001', 'DC-001', 'RET-001'],
    totalLeadTime: 25,
    riskScore: 0.15,
  },
  {
    id: 'PATH-002',
    product: 'Ibuprofen 200mg',
    path: ['SUP-002', 'FAC-001', 'WH-001', 'DC-002', 'RET-002'],
    totalLeadTime: 14,
    riskScore: 0.08,
  },
  {
    id: 'PATH-003',
    product: 'Vitamin C 1000mg',
    path: ['SUP-001', 'FAC-001', 'WH-001', 'DC-001', 'RET-001'],
    totalLeadTime: 11,
    riskScore: 0.05,
  },
];

const nodeIcons: Record<string, typeof Package> = {
  supplier: Factory,
  factory: Factory,
  warehouse: Package,
  dc: Truck,
  retailer: Store,
};

const nodeColors: Record<string, string> = {
  supplier: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  factory: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  warehouse: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  dc: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  retailer: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

export default function LineagePage() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredNodes = mockNodes.filter(
    (node) =>
      node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      node.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedNodeData = mockNodes.find((n) => n.id === selectedNode);
  const connectedEdges = mockEdges.filter(
    (e) => e.source === selectedNode || e.target === selectedNode
  );

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Supply Chain Lineage</h1>
          <p className="text-gray-400 mt-1">
            Graph visualization of supply chain relationships
          </p>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KpiTile title="Total Nodes" value={mockNodes.length.toString()} trend={0} />
        <KpiTile title="Suppliers" value="3" trend={0} />
        <KpiTile title="Avg Lead Time" value="18 days" trend={-5.2} />
        <KpiTile title="Avg Reliability" value="95.2%" trend={2.1} />
        <KpiTile title="Risk Paths" value="1" trend={-50.0} />
      </div>

      {/* Graph view + Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Graph visualization placeholder */}
        <GlassCard className="lg:col-span-2 h-[500px] flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Network Graph</h3>
            <div className="flex items-center gap-2">
              <button className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all">
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 rounded-lg bg-gray-800/50 border border-white/10 flex items-center justify-center relative overflow-hidden">
            {/* Simple node visualization */}
            <div className="absolute inset-0 p-8">
              {/* Tier labels */}
              <div className="absolute left-4 top-1/4 text-xs text-gray-500 -rotate-90 origin-left">
                Tier 2 Suppliers
              </div>
              <div className="absolute left-4 top-1/2 text-xs text-gray-500 -rotate-90 origin-left">
                Tier 1 Suppliers
              </div>
              <div className="absolute left-4 top-3/4 text-xs text-gray-500 -rotate-90 origin-left">
                Operations
              </div>

              {/* Node display */}
              <div className="flex flex-col items-center justify-center h-full gap-8">
                {/* Tier 2 */}
                <div className="flex gap-8">
                  {mockedNodes('tier2').map((node) => (
                    <NodeButton
                      key={node.id}
                      node={node}
                      selected={selectedNode === node.id}
                      onClick={() => setSelectedNode(node.id)}
                    />
                  ))}
                </div>
                
                {/* Tier 1 */}
                <div className="flex gap-8">
                  {mockedNodes('tier1').map((node) => (
                    <NodeButton
                      key={node.id}
                      node={node}
                      selected={selectedNode === node.id}
                      onClick={() => setSelectedNode(node.id)}
                    />
                  ))}
                </div>
                
                {/* Operations */}
                <div className="flex gap-8">
                  {mockedNodes('tier0').map((node) => (
                    <NodeButton
                      key={node.id}
                      node={node}
                      selected={selectedNode === node.id}
                      onClick={() => setSelectedNode(node.id)}
                    />
                  ))}
                </div>
                
                {/* Retailers */}
                <div className="flex gap-8">
                  {mockedNodes('retail').map((node) => (
                    <NodeButton
                      key={node.id}
                      node={node}
                      selected={selectedNode === node.id}
                      onClick={() => setSelectedNode(node.id)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Graph placeholder text */}
            <div className="absolute bottom-4 left-4 text-xs text-gray-500">
              Neo4j graph visualization with D3.js or vis.js
            </div>
          </div>
        </GlassCard>

        {/* Node details */}
        <GlassCard className="h-[500px] flex flex-col">
          <h3 className="font-semibold text-white mb-4">Node Details</h3>
          
          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes..."
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 transition-all"
            />
          </div>

          {selectedNodeData ? (
            <div className="flex-1 space-y-4">
              {/* Selected node info */}
              <div className="p-4 rounded-lg bg-white/5">
                <div className="flex items-center gap-3 mb-3">
                  {(() => {
                    const Icon = nodeIcons[selectedNodeData.type];
                    return (
                      <div className={cn('p-2 rounded-lg border', nodeColors[selectedNodeData.type])}>
                        <Icon className="w-5 h-5" />
                      </div>
                    );
                  })()}
                  <div>
                    <p className="font-medium text-white">{selectedNodeData.name}</p>
                    <p className="text-xs text-gray-400">{selectedNodeData.id}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Type:</span>
                    <span className="ml-2 text-white capitalize">{selectedNodeData.type}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Tier:</span>
                    <span className="ml-2 text-white">{selectedNodeData.tier}</span>
                  </div>
                </div>
              </div>

              {/* Connected edges */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">Connections</h4>
                <div className="space-y-2">
                  {connectedEdges.map((edge) => {
                    const isSource = edge.source === selectedNode;
                    const otherNodeId = isSource ? edge.target : edge.source;
                    const otherNode = mockNodes.find((n) => n.id === otherNodeId);
                    
                    return (
                      <div
                        key={`${edge.source}-${edge.target}`}
                        className="p-3 rounded-lg bg-white/5 text-sm"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-white">{otherNode?.name}</span>
                          <span className={cn(
                            'text-xs',
                            isSource ? 'text-emerald-400' : 'text-indigo-400'
                          )}>
                            {isSource ? 'Outbound →' : '← Inbound'}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-400">
                          <span>Lead time: {edge.leadTime}d</span>
                          <span>Reliability: {(edge.reliability * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              Select a node to view details
            </div>
          )}
        </GlassCard>
      </div>

      {/* Product pathways */}
      <GlassCard>
        <h3 className="font-semibold text-white mb-4">Product Pathways</h3>
        <DataTable
          data={mockPathways}
          columns={[
            {
              key: 'id',
              header: 'Pathway ID',
              sortable: true,
              className: 'font-mono text-indigo-400',
            },
            {
              key: 'product',
              header: 'Product',
              sortable: true,
            },
            {
              key: 'path',
              header: 'Path',
              accessor: (row) => (
                <div className="flex items-center gap-1">
                  {(row.path as string[]).map((nodeId, i) => (
                    <span key={i} className="flex items-center gap-1">
                      <span className="text-xs text-gray-400">{nodeId}</span>
                      {i < (row.path as string[]).length - 1 && (
                        <span className="text-gray-600">→</span>
                      )}
                    </span>
                  ))}
                </div>
              ),
            },
            {
              key: 'totalLeadTime',
              header: 'Lead Time',
              sortable: true,
              accessor: (row) => `${row.totalLeadTime} days`,
            },
            {
              key: 'riskScore',
              header: 'Risk',
              sortable: true,
              accessor: (row) => {
                const risk = row.riskScore as number;
                return (
                  <span className={cn(
                    risk < 0.1 ? 'text-emerald-400' :
                    risk < 0.15 ? 'text-amber-400' : 'text-rose-400'
                  )}>
                    {(risk * 100).toFixed(0)}%
                  </span>
                );
              },
            },
          ]}
          pageSize={5}
          searchPlaceholder="Search pathways..."
        />
      </GlassCard>
    </div>
  );
}

// Helper to group nodes by tier
function mockedNodes(tier: string) {
  const tierMap: Record<string, number[]> = {
    tier2: [2],
    tier1: [1],
    tier0: [0],
    retail: [-1],
  };
  return mockNodes.filter((n) => tierMap[tier].includes(n.tier));
}

// Node button component
function NodeButton({
  node,
  selected,
  onClick,
}: {
  node: typeof mockNodes[0];
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = nodeIcons[node.type];
  
  return (
    <button
      onClick={onClick}
      className={cn(
        'p-3 rounded-lg border transition-all',
        nodeColors[node.type],
        selected && 'ring-2 ring-white/50 scale-110'
      )}
      title={node.name}
    >
      <Icon className="w-5 h-5" />
    </button>
  );
}

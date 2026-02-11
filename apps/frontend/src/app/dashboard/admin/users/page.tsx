// =============================================================================
// IndigoGlass Nexus - Admin Users Page
// =============================================================================

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users,
  UserPlus,
  Shield,
  MoreHorizontal,
  Pencil,
  Trash2,
  Check,
  X,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { KpiTile } from '@/components/ui/kpi-tile';
import { DataTable } from '@/components/ui/data-table';
import { useToaster } from '@/components/ui/toaster';
import { cn, formatDate } from '@/lib/utils';

// Mock users data
const mockUsers = [
  {
    id: '1',
    email: 'admin@indigoglass.com',
    name: 'System Admin',
    role: 'Admin',
    status: 'active',
    lastLogin: '2024-01-15T10:30:00Z',
    createdAt: '2023-06-01T00:00:00Z',
  },
  {
    id: '2',
    email: 'analyst@indigoglass.com',
    name: 'Data Analyst',
    role: 'Analyst',
    status: 'active',
    lastLogin: '2024-01-14T15:45:00Z',
    createdAt: '2023-08-15T00:00:00Z',
  },
  {
    id: '3',
    email: 'viewer@indigoglass.com',
    name: 'Report Viewer',
    role: 'Viewer',
    status: 'active',
    lastLogin: '2024-01-13T09:00:00Z',
    createdAt: '2023-10-20T00:00:00Z',
  },
  {
    id: '4',
    email: 'operations@indigoglass.com',
    name: 'Ops Manager',
    role: 'Analyst',
    status: 'inactive',
    lastLogin: '2023-12-01T14:20:00Z',
    createdAt: '2023-07-10T00:00:00Z',
  },
  {
    id: '5',
    email: 'logistics@indigoglass.com',
    name: 'Logistics Lead',
    role: 'Analyst',
    status: 'active',
    lastLogin: '2024-01-15T08:15:00Z',
    createdAt: '2023-09-05T00:00:00Z',
  },
];

const roleColors: Record<string, string> = {
  Admin: 'bg-rose-500/20 text-rose-400',
  Analyst: 'bg-indigo-500/20 text-indigo-400',
  Viewer: 'bg-gray-500/20 text-gray-400',
};

const statusColors: Record<string, string> = {
  active: 'bg-emerald-500/20 text-emerald-400',
  inactive: 'bg-gray-500/20 text-gray-400',
};

export default function AdminUsersPage() {
  const toaster = useToaster();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUser, setEditingUser] = useState<typeof mockUsers[0] | null>(null);

  const activeUsers = mockUsers.filter((u) => u.status === 'active').length;
  const adminCount = mockUsers.filter((u) => u.role === 'Admin').length;
  const analystCount = mockUsers.filter((u) => u.role === 'Analyst').length;
  const viewerCount = mockUsers.filter((u) => u.role === 'Viewer').length;

  const handleDeleteUser = (userId: string) => {
    toaster.success('User Deleted', 'User has been removed from the system');
  };

  const handleToggleStatus = (userId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    toaster.info('Status Updated', `User is now ${newStatus}`);
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">User Management</h1>
          <p className="text-gray-400 mt-1">
            Manage system users and access permissions
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500 text-white font-medium text-sm hover:bg-indigo-600 transition-all"
        >
          <UserPlus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiTile title="Total Users" value={mockUsers.length.toString()} trend={0} />
        <KpiTile title="Active Users" value={activeUsers.toString()} trend={0} />
        <KpiTile title="Admins" value={adminCount.toString()} trend={0} />
        <KpiTile title="Analysts" value={analystCount.toString()} trend={0} />
      </div>

      {/* Users table */}
      <GlassCard>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white">All Users</h3>
          <div className="flex gap-2">
            {Object.entries(roleColors).map(([role, color]) => (
              <span
                key={role}
                className={cn('inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs', color)}
              >
                <Shield className="w-3 h-3" />
                {role}
              </span>
            ))}
          </div>
        </div>
        
        <DataTable
          data={mockUsers}
          columns={[
            {
              key: 'name',
              header: 'Name',
              sortable: true,
              accessor: (row) => (
                <div>
                  <p className="font-medium text-white">{row.name}</p>
                  <p className="text-xs text-gray-500">{row.email}</p>
                </div>
              ),
            },
            {
              key: 'role',
              header: 'Role',
              sortable: true,
              accessor: (row) => (
                <span className={cn('px-2 py-1 rounded text-xs', roleColors[row.role as string])}>
                  {row.role}
                </span>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              sortable: true,
              accessor: (row) => (
                <span className={cn('px-2 py-1 rounded text-xs capitalize', statusColors[row.status as string])}>
                  {row.status}
                </span>
              ),
            },
            {
              key: 'lastLogin',
              header: 'Last Login',
              sortable: true,
              accessor: (row) => (
                <span className="text-gray-400">
                  {formatDate(row.lastLogin as string)}
                </span>
              ),
            },
            {
              key: 'createdAt',
              header: 'Created',
              sortable: true,
              accessor: (row) => (
                <span className="text-gray-400">
                  {formatDate(row.createdAt as string)}
                </span>
              ),
            },
            {
              key: 'actions',
              header: '',
              accessor: (row) => (
                <div className="flex items-center gap-1 justify-end">
                  <button
                    onClick={() => handleToggleStatus(row.id as string, row.status as string)}
                    className={cn(
                      'p-1.5 rounded-lg transition-all',
                      row.status === 'active'
                        ? 'text-gray-400 hover:text-amber-400 hover:bg-amber-500/10'
                        : 'text-gray-400 hover:text-emerald-400 hover:bg-emerald-500/10'
                    )}
                    title={row.status === 'active' ? 'Deactivate' : 'Activate'}
                  >
                    {row.status === 'active' ? <X className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => setEditingUser(row as typeof mockUsers[0])}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-all"
                    title="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteUser(row.id as string)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ),
            },
          ]}
          pageSize={10}
          searchPlaceholder="Search users..."
        />
      </GlassCard>

      {/* Add/Edit User Modal */}
      {(showAddModal || editingUser) && (
        <UserModal
          user={editingUser}
          onClose={() => {
            setShowAddModal(false);
            setEditingUser(null);
          }}
          onSave={(data) => {
            if (editingUser) {
              toaster.success('User Updated', 'User details have been saved');
            } else {
              toaster.success('User Created', 'New user has been added');
            }
            setShowAddModal(false);
            setEditingUser(null);
          }}
        />
      )}
    </div>
  );
}

// User modal component
function UserModal({
  user,
  onClose,
  onSave,
}: {
  user: typeof mockUsers[0] | null;
  onClose: () => void;
  onSave: (data: Partial<typeof mockUsers[0]>) => void;
}) {
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    role: user?.role || 'Viewer',
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md rounded-xl bg-gray-900/95 border border-white/10 shadow-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          {user ? 'Edit User' : 'Add New User'}
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 transition-all"
              placeholder="Enter name"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 transition-all"
              placeholder="Enter email"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:border-indigo-500/50 transition-all"
            >
              <option value="Viewer">Viewer</option>
              <option value="Analyst">Analyst</option>
              <option value="Admin">Admin</option>
            </select>
          </div>
        </div>
        
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(formData)}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-indigo-500 text-white hover:bg-indigo-600 transition-all"
          >
            {user ? 'Save Changes' : 'Create User'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// IndigoGlass Nexus - Sidebar Navigation Component
// =============================================================================

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Truck,
  Leaf,
  GitBranch,
  Settings,
  Download,
  Users,
  LogOut,
} from 'lucide-react';

const navItems = [
  {
    section: 'Analytics',
    items: [
      { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
      { href: '/dashboard/forecast', label: 'Forecast', icon: TrendingUp },
      { href: '/dashboard/inventory', label: 'Inventory', icon: Package },
      { href: '/dashboard/optimizer', label: 'Optimizer', icon: Truck },
      { href: '/dashboard/sustainability', label: 'Sustainability', icon: Leaf },
      { href: '/dashboard/lineage', label: 'Lineage', icon: GitBranch },
    ],
  },
  {
    section: 'Tools',
    items: [
      { href: '/dashboard/exports', label: 'Exports', icon: Download },
    ],
  },
  {
    section: 'Admin',
    items: [
      { href: '/dashboard/admin/users', label: 'Users', icon: Users },
      { href: '/dashboard/admin/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 bg-gray-900/95 backdrop-blur-xl border-r border-white/10 overflow-y-auto">
      <div className="py-4">
        {navItems.map((section) => (
          <div key={section.section} className="mb-6">
            <div className="px-4 mb-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {section.section}
              </span>
            </div>
            <nav className="space-y-1 px-2">
              {section.items.map((item) => {
                const isActive = pathname === item.href || 
                  (item.href !== '/dashboard' && pathname.startsWith(item.href));
                
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-indigo-500/20 text-indigo-400 border-l-2 border-indigo-500 ml-0.5'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Logout at bottom */}
      <div className="absolute bottom-4 left-0 right-0 px-4">
        <button
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-rose-500/20 hover:text-rose-400 transition-all duration-200"
          onClick={() => {
            // Handle logout
          }}
        >
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>
    </aside>
  );
}

import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Palette, 
  Layers, 
  DollarSign, 
  Building2, 
  Clock, 
  Users 
} from 'lucide-react';
import useAuth from '../../features/auth/useAuth';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  
  if (!user) return null;

  // Common links for all users
  const commonLinks = [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  ];

  // Role-specific links
  const architectLinks = [
    { to: '#designs', label: 'Design Canvas', icon: Palette },
    { to: '#blueprints', label: 'Blueprints', icon: Layers },
    { to: '#materials', label: 'Materials Library', icon: Building2 },
  ];

  const contractorLinks = [
    { to: '#estimates', label: 'Cost Estimator', icon: DollarSign },
    { to: '#scheduling', label: 'Project Scheduling', icon: Clock },
    { to: '#subcontractors', label: 'Subcontractors', icon: Users },
  ];

  const links = [
    ...commonLinks,
    ...(user.role === 'Architect' ? architectLinks : contractorLinks),
  ];

  return (
    <aside className="w-64 border-r border-zinc-200 bg-white min-h-[calc(100vh-65px)] p-4 flex flex-col gap-6">
      <div>
        <h2 className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-3 mb-3">
          Navigation
        </h2>
        <nav className="flex flex-col gap-1">
          {links.map((link) => {
            const Icon = link.icon;
            const isPlaceholder = link.to.startsWith('#');
            
            return isPlaceholder ? (
              // Mock items that aren't routed yet
              <div
                key={link.label}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 cursor-not-allowed hover:bg-zinc-50/50 transition-colors"
                title="Coming soon"
              >
                <Icon size={18} />
                <span>{link.label}</span>
                <span className="ml-auto text-[9px] bg-zinc-100 text-zinc-500 font-bold px-1.5 py-0.5 rounded uppercase">
                  Soon
                </span>
              </div>
            ) : (
              // Actual router nav link
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-indigo-50/75 text-indigo-700 font-semibold'
                      : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-950'
                  }`
                }
              >
                <Icon size={18} />
                <span>{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto border-t border-zinc-100 pt-4 px-3 text-center">
        <p className="text-[11px] text-zinc-400 font-medium leading-normal">
          Logged in as <span className="font-bold text-zinc-600">{user.role}</span>
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;

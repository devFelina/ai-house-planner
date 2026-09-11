import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  PlusSquare
} from 'lucide-react';
import useAuth from '../../features/auth/useAuth';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  
  if (!user) return null;

  // Common links for all users
  const links = [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
    { to: '/dashboard/new-project', label: 'New Project (Intake)', icon: PlusSquare },
  ];

  return (
    <aside className="w-64 border-r border-zinc-200/50 bg-white/80 backdrop-blur-xl min-h-[calc(100vh-65px)] p-4 flex flex-col gap-6 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)] z-10">
      <div>
        <h2 className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-3 mb-3">
          Navigation
        </h2>
        <nav className="flex flex-col gap-1.5">
          {links.map((link) => {
            const Icon = link.icon;
            
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/dashboard'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-50 to-white text-indigo-700 font-semibold shadow-sm border border-indigo-100/50'
                      : 'text-zinc-500 hover:bg-zinc-50/80 hover:text-zinc-900 border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={isActive ? 'text-indigo-600' : 'text-zinc-400'} />
                    <span>{link.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto border-t border-zinc-100 pt-4 px-3 text-center bg-zinc-50/50 rounded-xl pb-2">
        <p className="text-[11px] text-zinc-400 font-medium leading-normal">
          Logged in as <span className="font-bold text-zinc-700 bg-white px-2 py-0.5 rounded shadow-sm border border-zinc-100 ml-1">{user.role}</span>
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;

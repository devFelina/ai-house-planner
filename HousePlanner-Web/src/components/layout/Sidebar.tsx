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
    <aside className="w-64 border-r border-zinc-200/50 dark:border-gray-800/50 bg-white/80 dark:bg-gray-950/80 backdrop-blur-xl min-h-[calc(100vh-65px)] p-4 flex flex-col gap-6 shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)] z-10 transition-colors duration-300">
      <div>
        <h2 className="text-[10px] font-bold text-zinc-400 dark:text-gray-500 uppercase tracking-wider px-3 mb-3">
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
                      ? 'bg-gradient-to-r from-indigo-50 to-white dark:from-indigo-900/30 dark:to-gray-900 text-indigo-700 dark:text-indigo-400 font-semibold shadow-sm border border-indigo-100/50 dark:border-indigo-800/30'
                      : 'text-zinc-500 dark:text-gray-400 hover:bg-zinc-50/80 dark:hover:bg-gray-900/50 hover:text-zinc-900 dark:hover:text-gray-200 border border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} className={isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-zinc-400 dark:text-gray-500'} />
                    <span>{link.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto border-t border-zinc-100 dark:border-gray-800/50 pt-4 px-3 text-center bg-zinc-50/50 dark:bg-gray-900/30 rounded-xl pb-2 transition-colors duration-300">
        <p className="text-[11px] text-zinc-400 dark:text-gray-500 font-medium leading-normal">
          Logged in as <span className="font-bold text-zinc-700 dark:text-gray-300 bg-white dark:bg-gray-800 px-2 py-0.5 rounded shadow-sm border border-zinc-100 dark:border-gray-700 ml-1">{user.role}</span>
        </p>
      </div>
    </aside>
  );
};

export default Sidebar;

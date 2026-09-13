import React from 'react';
import { LogOut, User, Box, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import useAuth from '../../features/auth/useAuth';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const handleLogout = () => {
    logout();
    window.location.href = '/';
  };

  return (
    <header className="sticky top-0 z-30 w-full bg-white/70 dark:bg-gray-950/70 backdrop-blur-xl border-b border-zinc-200/50 dark:border-gray-800/50 px-6 py-3.5 flex items-center justify-between shadow-[0_4px_30px_rgba(0,0,0,0.03)] transition-colors duration-300">
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 relative flex items-center justify-center">
            <Box className="absolute text-gray-900 dark:text-white transition-colors" size={24} strokeWidth={1.5} />
            <Sparkles className="absolute text-yellow-600 -top-1 -right-1" size={12} />
          </div>
          <div>
            <span className="text-sm font-bold text-gray-900 dark:text-white tracking-[0.2em] transition-colors">HOMEPLANNER<span className="text-gray-400">AI</span></span>
            <span className="text-[9px] text-indigo-500 font-bold uppercase tracking-widest block leading-none ml-0.5 mt-0.5">Console</span>
          </div>
        </Link>
      </div>

      {user && (
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-3 bg-zinc-50/80 dark:bg-gray-900 border border-zinc-200/50 dark:border-gray-800 rounded-xl px-3 py-1.5 shadow-sm transition-colors">
            <div className="bg-zinc-200/50 dark:bg-gray-800 p-1.5 rounded-lg text-zinc-600 dark:text-gray-400 transition-colors">
              <User size={14} />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-bold text-zinc-800 dark:text-gray-200 leading-none transition-colors">{user.email}</span>
              <span className="text-[10px] text-zinc-500 dark:text-gray-500 font-semibold uppercase mt-1 tracking-wider leading-none transition-colors">
                {user.role}
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="group flex items-center gap-2 px-3 py-2 rounded-xl text-zinc-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50/80 dark:hover:bg-red-900/20 border border-transparent hover:border-red-100 dark:hover:border-red-900/50 transition-all shadow-sm hover:shadow"
          >
            <LogOut size={16} className="group-hover:-translate-x-0.5 transition-transform" />
            <span className="hidden sm:inline text-sm font-semibold">Sign Out</span>
          </button>
        </div>
      )}
    </header>
  );
};

export default Navbar;

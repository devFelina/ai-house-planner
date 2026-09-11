import React from 'react';
import { LogOut, Home, User } from 'lucide-react';
import useAuth from '../../features/auth/useAuth';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 w-full bg-white/70 backdrop-blur-xl border-b border-zinc-200/50 px-6 py-3.5 flex items-center justify-between shadow-[0_4px_30px_rgba(0,0,0,0.03)]">
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-br from-indigo-500 to-indigo-700 p-2 rounded-xl text-white shadow-md shadow-indigo-200">
          <Home size={18} className="drop-shadow-sm" />
        </div>
        <div>
          <span className="font-extrabold text-zinc-900 text-lg tracking-tight">HousePlanner</span>
          <span className="text-[10px] text-indigo-500 font-bold uppercase tracking-widest block leading-none ml-0.5 mt-0.5">Console</span>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-3 bg-zinc-50/80 border border-zinc-200/50 rounded-xl px-3 py-1.5 shadow-sm">
            <div className="bg-zinc-200/50 p-1.5 rounded-lg text-zinc-600">
              <User size={14} />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-bold text-zinc-800 leading-none">{user.email}</span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase mt-1 tracking-wider leading-none">
                {user.role}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            className="group flex items-center gap-2 px-3 py-2 rounded-xl text-zinc-500 hover:text-red-600 hover:bg-red-50/80 border border-transparent hover:border-red-100 transition-all shadow-sm hover:shadow"
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

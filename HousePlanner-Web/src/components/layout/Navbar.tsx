import React from 'react';
import { LogOut, Home, User } from 'lucide-react';
import useAuth from '../../features/auth/useAuth';
import Button from '../common/Button';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 w-full glassmorphism border-b border-zinc-200/80 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="bg-indigo-600 p-2 rounded-lg text-white">
          <Home size={18} />
        </div>
        <div>
          <span className="font-bold text-zinc-950 text-base tracking-tight">HousePlanner</span>
          <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block leading-none">Console</span>
        </div>
      </div>

      {user && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-zinc-50 border border-zinc-100 rounded-lg px-3 py-1.5">
            <div className="bg-zinc-200 p-1 rounded-full text-zinc-600">
              <User size={14} />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-medium text-zinc-700 leading-none">{user.email}</span>
              <span className="text-[10px] text-zinc-400 font-bold uppercase mt-0.5 tracking-wider leading-none">
                {user.role}
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={logout}
            className="text-zinc-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50/50 flex items-center gap-1.5"
          >
            <LogOut size={14} />
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      )}
    </header>
  );
};

export default Navbar;

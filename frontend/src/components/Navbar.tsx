import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Mic, LayoutDashboard, LogOut, MessageSquare } from 'lucide-react';

interface NavbarProps {
  currentTab: 'coach' | 'dashboard';
  setCurrentTab: (tab: 'coach' | 'dashboard') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, setCurrentTab }) => {
  const { user, logout } = useAuth();

  return (
    <nav className="glass-panel sticky top-0 z-50 w-full px-3 sm:px-6 py-3 sm:py-4 flex items-center justify-between border-b border-white/5 shadow-lg shadow-black/20 gap-2">
      {/* Branding */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
          <Mic className="w-4 h-4 sm:w-5 sm:h-5 text-white animate-pulse-slow" />
        </div>
        <div className="hidden xs:block sm:block">
          <span className="font-bold text-lg sm:text-xl tracking-tight bg-gradient-to-r from-white via-slate-200 to-violet-400 bg-clip-text text-transparent">
            TalkBuddy
          </span>
          <span className="text-xs block text-violet-400/80 font-medium tracking-wide uppercase hidden sm:block">
            AI Speaking Coach
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 sm:gap-2">
        <button
          onClick={() => setCurrentTab('coach')}
          className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all duration-200 ${
            currentTab === 'coach'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-500/10'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span className="hidden sm:inline">Speaking Coach</span>
        </button>
        <button
          onClick={() => setCurrentTab('dashboard')}
          className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all duration-200 ${
            currentTab === 'dashboard'
              ? 'bg-violet-600 text-white shadow-md shadow-violet-500/10'
              : 'text-slate-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span className="hidden sm:inline">Dashboard</span>
        </button>
      </div>

      {/* User Actions */}
      <div className="flex items-center gap-2 sm:gap-4 shrink-0">
        {user && (
          <div className="hidden md:flex flex-col items-end">
            <span className="text-sm font-semibold text-slate-200">{user.username}</span>
            <span className="text-xs text-slate-400 font-medium">Student Account</span>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3.5 py-2 rounded-xl text-sm font-medium border border-white/5 text-slate-400 hover:text-white hover:bg-red-500/10 hover:border-red-500/20 transition-all duration-200"
          title="Sign Out"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden md:inline">Logout</span>
        </button>
      </div>
    </nav>
  );
};

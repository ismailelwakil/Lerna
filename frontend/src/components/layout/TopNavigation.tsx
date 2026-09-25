import React from 'react';
import { Menu, BookMarked, Sparkles, Shield } from 'lucide-react';
import { useStudent } from '../../context/StudentContext';
import { LanguageSelector } from '../common/LanguageSelector';

interface TopNavigationProps {
  onToggleMobileMenu: () => void;
}

export const TopNavigation: React.FC<TopNavigationProps> = ({ onToggleMobileMenu }) => {
  const { profile, studentId } = useStudent();

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 md:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg">
          <BookMarked className="w-4 h-4 text-indigo-600" />
          <span className="font-semibold text-slate-800">{profile?.course || 'General'}</span>
          <span className="text-slate-400">·</span>
          <span className="text-slate-500 font-mono text-[11px]">{studentId}</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 border border-indigo-200 rounded-md text-[11px] font-medium text-indigo-800">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>Style: {profile?.learning_preference || 'step-by-step'}</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-md text-[11px] font-medium text-emerald-800">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span className="hidden sm:inline">Trust: 0.80</span>
        </div>

        <LanguageSelector compact />
      </div>
    </header>
  );
};

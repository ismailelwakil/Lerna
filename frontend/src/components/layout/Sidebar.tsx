import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  GraduationCap,
  FolderOpen,
  Sparkles,
  ClipboardCheck,
  User,
  Server,
  BookOpen,
} from 'lucide-react';
import { useStudent } from '../../context/StudentContext';
import { t } from '../../utils/i18n';

interface SidebarProps {
  className?: string;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  className = '',
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const { profile, language } = useStudent();

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: t('nav_dashboard', language) },
    { to: '/tutor', icon: MessageSquare, label: t('nav_tutor', language) },
    { to: '/learning', icon: GraduationCap, label: t('nav_learning', language) },
    { to: '/materials', icon: FolderOpen, label: t('nav_materials', language) },
    { to: '/study-tools', icon: Sparkles, label: t('nav_study_tools', language) },
    { to: '/assessment', icon: ClipboardCheck, label: t('nav_assessment', language) },
    { to: '/profile', icon: User, label: t('nav_profile', language) },
    { to: '/system', icon: Server, label: t('nav_system', language) },
  ];

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-64 bg-slate-900 text-slate-300 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
        isMobileOpen ? 'translate-x-0' : '-translate-x-full'
      } ${className}`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800 bg-slate-950">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center text-white shadow-md">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-white text-base tracking-tight">Academic OS</span>
          <span className="text-[10px] block font-mono text-indigo-400 font-semibold tracking-wider">
            AI LEARNING PLATFORM
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Profile & Context Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-indigo-900/60 border border-indigo-700/50 flex items-center justify-center text-indigo-300 font-bold text-xs">
            {profile?.name ? profile.name.charAt(0).toUpperCase() : 'S'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-white truncate">
              {profile?.name || 'Demo Student'}
            </p>
            <p className="text-[11px] text-slate-400 truncate">
              {profile?.course || 'Computer Science'}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

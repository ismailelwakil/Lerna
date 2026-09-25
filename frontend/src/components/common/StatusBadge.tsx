import React from 'react';

interface StatusBadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = '' }) => {
  const norm = status.toLowerCase();

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';
  if (['indexed', 'mastered', 'success', 'completed', 'high'].includes(norm)) {
    colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (['weak', 'pending', 'medium', 'warning'].includes(norm)) {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (['unknown', 'missing_knowledge', 'failed', 'low', 'danger'].includes(norm)) {
    colorClasses = 'bg-rose-50 text-rose-700 border-rose-200';
  } else if (['processing', 'info'].includes(norm)) {
    colorClasses = 'bg-blue-50 text-blue-700 border-blue-200';
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${colorClasses} ${className}`}
    >
      {label || status}
    </span>
  );
};

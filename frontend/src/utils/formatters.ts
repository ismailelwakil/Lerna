/**
 * Data Formatting Utilities
 */

export function formatPercentage(val: number): string {
  return `${Math.round(val * 100)}%`;
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return 'N/A';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function getMasteryColor(mastery: number): string {
  if (mastery >= 0.7) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
  if (mastery > 0.0) return 'text-amber-600 bg-amber-50 border-amber-200';
  return 'text-rose-600 bg-rose-50 border-rose-200';
}

export function getMasteryLabel(mastery: number): string {
  if (mastery >= 0.7) return 'Mastered Strength';
  if (mastery > 0.0) return 'Weak Attempted';
  return 'Missing Knowledge';
}

export function getPriorityBadgeColor(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'high':
      return 'bg-rose-100 text-rose-800 border-rose-300';
    case 'medium':
      return 'bg-amber-100 text-amber-800 border-amber-300';
    case 'low':
      return 'bg-blue-100 text-blue-800 border-blue-300';
    default:
      return 'bg-slate-100 text-slate-800 border-slate-300';
  }
}

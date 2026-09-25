import React from 'react';
import { ShieldCheck, FileText } from 'lucide-react';

interface SourceBadgeProps {
  sourceType: 'trusted_external' | 'student_upload' | string;
  authority?: string;
  trustScore?: number;
  className?: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  sourceType,
  authority,
  trustScore,
  className = '',
}) => {
  const isUpload = sourceType === 'student_upload';

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium border ${
        isUpload
          ? 'bg-blue-50 text-blue-700 border-blue-200'
          : 'bg-emerald-50 text-emerald-800 border-emerald-200'
      } ${className}`}
    >
      {isUpload ? (
        <>
          <FileText className="w-3.5 h-3.5 text-blue-600" />
          <span>Course Material</span>
        </>
      ) : (
        <>
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>
            Trusted External {authority ? `· ${authority}` : ''}{' '}
            {trustScore ? `(${Math.round(trustScore * 100)}%)` : ''}
          </span>
        </>
      )}
    </span>
  );
};

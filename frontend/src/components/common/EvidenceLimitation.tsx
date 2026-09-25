import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface EvidenceLimitationProps {
  message?: string;
  className?: string;
}

export const EvidenceLimitation: React.FC<EvidenceLimitationProps> = ({
  message = 'The retrieved evidence grounds the core mechanics, but specific sub-bounds or auxiliary complexities were omitted from the sources to prevent speculation.',
  className = '',
}) => {
  return (
    <div
      className={`p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-start gap-2.5 ${className}`}
    >
      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
      <div>
        <span className="font-semibold block mb-0.5">Evidence Limitation Notice</span>
        <span className="text-amber-800 leading-relaxed">{message}</span>
      </div>
    </div>
  );
};

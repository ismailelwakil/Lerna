import React from 'react';
import { useStudent } from '../../context/StudentContext';
import { SUPPORTED_LANGUAGES } from '../../utils/i18n';
import { Languages } from 'lucide-react';

interface LanguageSelectorProps {
  className?: string;
  compact?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  className = '',
  compact = false,
}) => {
  const { language, setLanguage } = useStudent();

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      <Languages className="w-4 h-4 text-slate-400 flex-shrink-0" />
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        className={`bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-700 py-1 px-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-colors ${
          compact ? 'w-24 text-[11px]' : 'w-36'
        }`}
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.native} ({lang.name})
          </option>
        ))}
      </select>
    </div>
  );
};

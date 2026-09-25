import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface QuestionBankViewerProps {
  content: string;
  className?: string;
}

export const QuestionBankViewer: React.FC<QuestionBankViewerProps> = ({
  content,
  className = '',
}) => {
  const [showAllSolutions, setShowAllSolutions] = useState(false);

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between text-xs text-slate-500 pb-2 border-b border-slate-200">
        <span className="font-semibold flex items-center gap-1.5">
          <HelpCircle className="w-4 h-4 text-indigo-600" />
          Grounded Question Bank & Rubrics
        </span>
        <button
          onClick={() => setShowAllSolutions(!showAllSolutions)}
          className="text-indigo-600 hover:text-indigo-800 font-medium"
        >
          {showAllSolutions ? 'Hide Rubrics' : 'Reveal All Rubrics & Solutions'}
        </button>
      </div>

      <div className="prose prose-sm max-w-none text-slate-800 bg-white p-6 rounded-xl border border-slate-200 shadow-sm leading-relaxed whitespace-pre-wrap font-sans">
        {content}
      </div>
    </div>
  );
};

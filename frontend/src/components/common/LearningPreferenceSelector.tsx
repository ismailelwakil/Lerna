import React from 'react';

const PREFERENCES = [
  { id: 'step-by-step', label: 'Step-by-Step Rigorous', desc: 'Detailed mechanical derivations from first principles' },
  { id: 'conceptual', label: 'Conceptual & High-Level', desc: 'Broad theoretical frameworks and big-picture intuition' },
  { id: 'practical-examples', label: 'Practical & Examples', desc: 'Code implementations, traces, and worked problems' },
  { id: 'exam-prep', label: 'Exam & Knowledge Check', desc: 'Concise definitions, pitfalls, and rubric criteria' },
] as const;

interface LearningPreferenceSelectorProps {
  value: string;
  onChange: (val: string) => void;
  className?: string;
}

export const LearningPreferenceSelector: React.FC<LearningPreferenceSelectorProps> = ({
  value,
  onChange,
  className = '',
}) => {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 gap-3 ${className}`}>
      {PREFERENCES.map((pref) => {
        const isSelected = value === pref.id;
        return (
          <div
            key={pref.id}
            onClick={() => onChange(pref.id)}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${
              isSelected
                ? 'bg-indigo-50 border-indigo-400 text-indigo-900 shadow-sm ring-1 ring-indigo-400'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <div className="font-semibold text-xs mb-1">{pref.label}</div>
            <div className="text-[11px] text-slate-500 leading-normal">{pref.desc}</div>
          </div>
        );
      })}
    </div>
  );
};

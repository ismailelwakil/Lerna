import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { materialsApi } from '../../api/materials';
import { useStudent } from '../../context/StudentContext';
import { FileText, Globe, Check } from 'lucide-react';

interface MaterialSelectorProps {
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  className?: string;
}

export const MaterialSelector: React.FC<MaterialSelectorProps> = ({
  selectedIds,
  onChange,
  className = '',
}) => {
  const { studentId, profile } = useStudent();

  const { data: materialsData, isLoading } = useQuery({
    queryKey: ['materials', studentId, profile?.course],
    queryFn: () => materialsApi.listMaterials(studentId, profile?.course),
    staleTime: 1000 * 60 * 2,
  });

  const materials = materialsData?.materials || [];

  const isTrustedExternalMode = selectedIds.length === 0;

  const toggleMaterial = (docId: string) => {
    if (selectedIds.includes(docId)) {
      onChange(selectedIds.filter((id) => id !== docId));
    } else {
      onChange([...selectedIds, docId]);
    }
  };

  const selectAll = () => {
    onChange([]);
  };

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between text-xs text-slate-600">
        <span className="font-semibold">Evidence Scope:</span>
        <button
          type="button"
          onClick={selectAll}
          className={`px-2 py-0.5 rounded transition-colors ${
            isTrustedExternalMode
              ? 'bg-indigo-100 text-indigo-700 font-medium'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Reset to All Materials (Trusted External)
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={selectAll}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-all ${
            isTrustedExternalMode
              ? 'bg-emerald-50 border-emerald-300 text-emerald-800 shadow-sm font-medium'
              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <Globe className="w-3.5 h-3.5 text-emerald-600" />
          <span>All Course Materials (Trusted External)</span>
          {isTrustedExternalMode && <Check className="w-3 h-3 text-emerald-600" />}
        </button>

        {isLoading && (
          <span className="text-xs text-slate-400 py-1.5">Loading uploaded materials...</span>
        )}

        {materials.map((mat) => {
          const isSelected = selectedIds.includes(mat.document_id);
          return (
            <button
              key={mat.document_id}
              type="button"
              onClick={() => toggleMaterial(mat.document_id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition-all ${
                isSelected
                  ? 'bg-blue-50 border-blue-300 text-blue-800 shadow-sm font-medium'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span className="max-w-[180px] truncate">{mat.filename}</span>
              {isSelected && <Check className="w-3 h-3 text-blue-600" />}
            </button>
          );
        })}
      </div>

      <div className="text-[11px] text-slate-500">
        {isTrustedExternalMode ? (
          <span className="text-emerald-700 font-medium">
            Active: Searches verified Tier-A university lecture notes & textbooks (MIT, CMU, Stanford, etc.)
          </span>
        ) : (
          <span className="text-blue-700 font-medium">
            Active: Source-constrained to {selectedIds.length} uploaded document(s). Zero external leakage.
          </span>
        )}
      </div>
    </div>
  );
};

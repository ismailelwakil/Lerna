import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Citation } from '../../api/types';
import { SourceBadge } from './SourceBadge';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-200 rounded-lg bg-white shadow-sm overflow-hidden text-sm">
      <div
        className="p-3 bg-slate-50 flex items-center justify-between cursor-pointer hover:bg-slate-100 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center">
            {index + 1}
          </span>
          <span className="font-semibold text-slate-800 line-clamp-1">
            {citation.title || citation.source}
          </span>
          {citation.page && (
            <span className="text-xs text-slate-500 font-mono">p. {citation.page}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <SourceBadge
            sourceType={citation.source_type}
            authority={citation.authority}
            trustScore={citation.trust_score}
          />
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="p-3 border-t border-slate-200 bg-white space-y-2">
          {citation.url && (
            <div className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 break-all">
              <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
              <a href={citation.url} target="_blank" rel="noopener noreferrer">
                {citation.url}
              </a>
            </div>
          )}

          {citation.excerpt ? (
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700 font-serif leading-relaxed italic">
              "{citation.excerpt}"
            </div>
          ) : (
            <div className="text-xs text-slate-400 italic">No excerpt snippet available.</div>
          )}
        </div>
      )}
    </div>
  );
};

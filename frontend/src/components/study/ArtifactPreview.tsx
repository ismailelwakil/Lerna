import React from 'react';
import { Download, FileCode, Presentation } from 'lucide-react';
import { GeneratedResource } from '../../api/types';
import { studyToolsApi } from '../../api/studyTools';

interface ArtifactPreviewProps {
  resource: GeneratedResource;
  className?: string;
}

export const ArtifactPreview: React.FC<ArtifactPreviewProps> = ({ resource, className = '' }) => {
  const isSvg = resource.filename?.endsWith('.svg') || resource.mime_type?.includes('svg');
  const isPptx = resource.filename?.endsWith('.pptx') || resource.mime_type?.includes('presentation');

  const downloadUrl = resource.filename
    ? studyToolsApi.getArtifactDownloadUrl(resource.filename)
    : resource.download_url;

  return (
    <div className={`border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm ${className}`}>
      <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isPptx ? (
            <Presentation className="w-5 h-5 text-amber-600" />
          ) : (
            <FileCode className="w-5 h-5 text-indigo-600" />
          )}
          <div>
            <div className="text-xs font-semibold text-slate-800">
              {resource.filename || `${resource.kind} artifact`}
            </div>
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-mono">
              {isPptx ? 'PowerPoint Presentation (.pptx)' : 'Scalable Vector Graphic (.svg)'}
            </div>
          </div>
        </div>

        {downloadUrl && (
          <a
            href={downloadUrl}
            download={resource.filename || 'artifact'}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Download File
          </a>
        )}
      </div>

      {isSvg && resource.content ? (
        <div className="p-6 bg-slate-50/50 flex flex-col items-center justify-center overflow-auto max-h-[500px]">
          <div
            className="w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:rounded-lg [&>svg]:shadow-sm"
            dangerouslySetInnerHTML={{ __html: resource.content }}
          />
        </div>
      ) : isPptx ? (
        <div className="p-8 text-center bg-slate-50/30">
          <Presentation className="w-12 h-12 text-amber-500 mx-auto mb-3" />
          <h4 className="text-sm font-semibold text-slate-800 mb-1">
            Grounded Slide Deck Ready
          </h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
            Generated using python-pptx from authoritative lecture notes. Download to view slides, notes, and visual layout.
          </p>
          {downloadUrl && (
            <a
              href={downloadUrl}
              download={resource.filename || 'presentation.pptx'}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium shadow-sm transition-colors"
            >
              <Download className="w-4 h-4" />
              Download .pptx Presentation
            </a>
          )}
        </div>
      ) : (
        <div className="p-6 text-center text-xs text-slate-500">
          Binary artifact generated and stored on the server.
        </div>
      )}
    </div>
  );
};

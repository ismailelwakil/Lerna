import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { learningApi } from '../api/learning';
import { PageHeader } from '../components/layout/PageHeader';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import {
  Server,
  ShieldCheck,
  Cpu,
  Database,
  Globe,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export const SystemPage: React.FC = () => {
  const { data: health, isLoading: healthLoading, error: healthError, refetch } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => learningApi.getHealth(),
    staleTime: 1000 * 30,
  });

  const { data: capabilities, isLoading: capLoading } = useQuery({
    queryKey: ['systemCapabilities'],
    queryFn: () => learningApi.getCapabilities(),
    staleTime: 1000 * 60 * 5,
  });

  if (healthLoading || capLoading) {
    return <LoadingState message="Querying system capabilities and health status..." />;
  }

  if (healthError || !health) {
    return (
      <ErrorState
        title="Could not connect to backend system API"
        message={healthError instanceof Error ? healthError.message : 'API server is offline.'}
        onRetry={refetch}
      />
    );
  }

  const aiStatus = health.ai_status || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Capabilities & Architecture Verification"
        subtitle="Inspection of AI subsystems, vector stores, trust thresholds, and provider modes."
      />

      {/* Grid of Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Overall System Health */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Health Status</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-lg font-bold text-slate-900">Operational</div>
          <p className="text-[11px] text-slate-500">FastAPI backend facade active</p>
        </div>

        {/* Trust Threshold */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Trust Threshold</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-lg font-bold text-emerald-700 font-mono">0.80 Strict</div>
          <p className="text-[11px] text-slate-500">Commercial / blog search rejected</p>
        </div>

        {/* Embedding Model */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Embeddings</span>
            <Cpu className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-sm font-bold text-slate-900 truncate">multilingual-e5-small</div>
          <p className="text-[11px] text-slate-500">Dimension: 384 · Chroma compatible</p>
        </div>

        {/* Vector Store */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Knowledge Base</span>
            <Database className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-lg font-bold text-slate-900">ChromaDB</div>
          <p className="text-[11px] text-slate-500">Collection: academic_knowledge</p>
        </div>
      </div>

      {/* Capabilities Details */}
      {capabilities && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Supported Content Types (15 Types) */}
          <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-600" />
              Supported Content Types ({capabilities.content_types.length})
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {capabilities.content_types.map((type) => (
                <span
                  key={type}
                  className="px-2.5 py-1 bg-slate-100 text-slate-800 rounded-md text-xs font-mono"
                >
                  {type}
                </span>
              ))}
            </div>
          </div>

          {/* Multilingual Support (10 Languages) */}
          <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-600" />
              Supported Languages ({capabilities.languages.length})
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {capabilities.languages.map((lang) => (
                <span
                  key={lang}
                  className="px-2.5 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-md text-xs font-mono font-semibold"
                >
                  {lang}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Raw Health & AI Subsystem State */}
      <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Server className="w-4 h-4 text-indigo-600" />
          Subsystem Diagnostics & Provider Status
        </h3>

        <pre className="p-4 bg-slate-900 text-slate-200 rounded-xl text-xs font-mono overflow-auto max-h-72 leading-relaxed">
          {JSON.stringify(aiStatus, null, 2)}
        </pre>
      </div>
    </div>
  );
};

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { learningApi } from '../api/learning';
import { useStudent } from '../context/StudentContext';
import { PageHeader } from '../components/layout/PageHeader';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { getPriorityBadgeColor, formatDate } from '../utils/formatters';
import {
  Calendar,
  History,
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

export const MyLearningPage: React.FC = () => {
  const { studentId, token } = useStudent();

  const { data: learningState, isLoading, error, refetch } = useQuery({
    queryKey: ['learningState', studentId],
    queryFn: () => learningApi.getLearningState(studentId, token),
    staleTime: 1000 * 60 * 2,
  });

  if (isLoading) {
    return <LoadingState message="Loading your comprehensive learning analytics..." />;
  }

  if (error || !learningState) {
    return (
      <ErrorState
        title="Could not load learning profile"
        message={error instanceof Error ? error.message : 'Backend service is unavailable.'}
        onRetry={refetch}
      />
    );
  }

  const { profile: p, study_plan, learning_history } = learningState;

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Learning Analytics & Study Pathway"
        subtitle={`Hierarchical concept mastery, diagnostic assessment history, and personalized targets for ${p.name}.`}
        actions={
          <Link
            to="/assessment"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
          >
            Take Knowledge Check
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        }
      />

      {/* Concept Breakdown Categories */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Strengths */}
        <div className="p-4 bg-white rounded-xl border border-emerald-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              Mastered Strengths
            </span>
            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
              {p.strengths.length}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Concepts verified $\ge 70\%$ mastery. Tutor provides concise higher-level scaffolding without introductory basics.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {p.strengths.length === 0 ? (
              <span className="text-xs text-slate-400 italic">No confirmed strengths yet.</span>
            ) : (
              p.strengths.map((str) => (
                <span
                  key={str}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-900 border border-emerald-200"
                >
                  {str}
                </span>
              ))
            )}
          </div>
        </div>

        {/* Weak Attempted Concepts */}
        <div className="p-4 bg-white rounded-xl border border-amber-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Weak Attempted Concepts
            </span>
            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-amber-100 text-amber-800">
              {p.weak_concepts.length}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Concepts with attempted answers below target mastery. Tutor provides targeted reinforcement with error contrast.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {p.weak_concepts.length === 0 ? (
              <span className="text-xs text-slate-400 italic">No weak concepts recorded.</span>
            ) : (
              p.weak_concepts.map((wk) => (
                <span
                  key={wk}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200"
                >
                  {wk}
                </span>
              ))
            )}
          </div>
        </div>

        {/* Missing Knowledge */}
        <div className="p-4 bg-white rounded-xl border border-rose-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-rose-600" />
              Missing Knowledge
            </span>
            <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-rose-100 text-rose-800">
              {p.unknown_concepts.length}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Concepts flagged via "I don't know" or zero score. Tutor builds foundation from first principles without reproach.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {p.unknown_concepts.length === 0 ? (
              <span className="text-xs text-slate-400 italic">No missing knowledge gaps recorded.</span>
            ) : (
              p.unknown_concepts.map((un) => (
                <span
                  key={un}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-rose-50 text-rose-900 border border-rose-200"
                >
                  {un}
                </span>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Mastery Progress Bar List */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-indigo-600" />
          Mastery Matrix & Verified Target Thresholds
        </h3>

        <div className="space-y-3">
          {Object.entries(p.concept_mastery).map(([concept, val]) => {
            const pct = Math.round(val * 100);
            return (
              <div key={concept} className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">{concept}</span>
                  <span className="font-mono font-bold text-slate-700">{pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className={`h-full ${
                      pct >= 70 ? 'bg-emerald-500' : pct > 0 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${Math.max(pct, 4)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Personalized Study Plan Detail */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-indigo-600" />
          Personalized Study Plan Action Items
        </h3>

        <div className="space-y-3">
          {study_plan.map((item, idx) => (
            <div key={idx} className="p-4 border border-slate-200 rounded-lg bg-slate-50/40 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sm text-slate-800">{item.title}</span>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${getPriorityBadgeColor(item.priority)}`}>
                  {item.priority} priority
                </span>
              </div>
              <p className="text-xs text-slate-600">{item.reason}</p>
              <div className="space-y-1 pt-1">
                {item.recommended_actions.map((act, actIdx) => (
                  <div key={actIdx} className="flex items-center gap-2 text-xs text-slate-700">
                    <CheckCircle className="w-3.5 h-3.5 text-indigo-600 flex-shrink-0" />
                    <span>{act}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Learning Activity History */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <History className="w-4 h-4 text-indigo-600" />
          Recent Learning Interactions & Ingestion Provenance
        </h3>

        <div className="space-y-2 max-h-80 overflow-y-auto">
          {learning_history.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">No recent activity logged.</p>
          ) : (
            learning_history.slice(-10).reverse().map((act, idx) => (
              <div key={idx} className="p-3 border border-slate-100 rounded-lg bg-slate-50/50 flex items-start justify-between text-xs">
                <div className="space-y-1">
                  <div className="font-semibold text-slate-800">{act.query || act.topic || 'Query'}</div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span>Source: {act.knowledge_source || 'trusted_external'}</span>
                    <span>·</span>
                    <span>Lang: {act.language || 'en'}</span>
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  {formatDate(act.timestamp)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

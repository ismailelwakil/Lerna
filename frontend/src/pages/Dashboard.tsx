import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { learningApi } from '../api/learning';
import { spacedRepetitionApi } from '../api/spacedRepetition';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import { PageHeader } from '../components/layout/PageHeader';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { getPriorityBadgeColor } from '../utils/formatters';
import {
  Sparkles,
  ArrowRight,
  GraduationCap,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Calendar,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { studentId, token } = useStudent();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const { data: learningState, isLoading, error, refetch } = useQuery({
    queryKey: ['learningState', studentId],
    queryFn: () => learningApi.getLearningState(studentId, token),
    staleTime: 1000 * 60 * 2,
  });

  const reviewMutation = useMutation({
    mutationFn: ({ concept, remembered }: { concept: string; remembered: boolean }) =>
      spacedRepetitionApi.recordReview({ student_id: studentId, concept, remembered }, token),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['learningState', studentId] });
      queryClient.invalidateQueries({ queryKey: ['studentProfile', studentId] });
      addToast({
        type: 'success',
        title: 'Review Recorded',
        message: `Updated spaced interval for '${res.concept}' (${res.remembered ? 'Remembered' : 'Needs Review'}).`,
      });
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Review Error',
        message: err instanceof Error ? err.message : 'Could not record review.',
      });
    },
  });

  if (isLoading) {
    return <LoadingState message="Loading your personalized dashboard & intelligence metrics..." />;
  }

  if (error || !learningState) {
    return (
      <ErrorState
        title="Unable to load learning dashboard"
        message={error instanceof Error ? error.message : 'Backend service is unavailable.'}
        onRetry={refetch}
      />
    );
  }

  const { next_action, study_plan, review_queue, profile: p } = learningState;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${p.name || 'Scholar'}`}
        subtitle={`Active Course: ${p.course} · Style: ${p.learning_preference}`}
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/tutor"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              Ask AI Tutor
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        }
      />

      {/* Next Best Action Card (NBA) */}
      {next_action && (
        <div className="p-5 rounded-xl bg-gradient-to-r from-indigo-900 to-slate-900 text-white shadow-md relative overflow-hidden">
          <div className="flex items-start justify-between gap-4 relative z-10">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  <Sparkles className="w-3 h-3 text-indigo-300" />
                  Next Best Action
                </span>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                    next_action.priority === 'high'
                      ? 'bg-rose-500/30 text-rose-200 border border-rose-400/30'
                      : 'bg-amber-500/30 text-amber-200 border border-amber-400/30'
                  }`}
                >
                  {next_action.priority} priority
                </span>
              </div>
              <h2 className="text-lg font-bold text-white capitalize">
                {next_action.action.replace('_', ' ')}: {next_action.target_concepts.join(', ')}
              </h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                {next_action.reason}
              </p>
              {next_action.recommended_resources.length > 0 && (
                <div className="flex items-center gap-2 pt-2">
                  <span className="text-xs text-slate-400">Recommended tools:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {next_action.recommended_resources.map((res) => (
                      <Link
                        key={res}
                        to={`/study-tools?topic=${encodeURIComponent(next_action.target_concepts[0] || '')}&tool=${res}`}
                        className="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-indigo-200 text-xs font-mono transition-colors"
                      >
                        {res}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Link
              to="/tutor"
              className="hidden sm:inline-flex items-center gap-1 px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg text-xs font-semibold shadow transition-colors flex-shrink-0"
            >
              Start Focus Session
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      )}

      {/* Grid: Concept Mastery & Spaced Repetition */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Concept Mastery Overview (2 Columns) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-indigo-600" />
              Hierarchical Concept Mastery
            </h3>
            <Link to="/learning" className="text-xs font-medium text-indigo-600 hover:text-indigo-800">
              View Detailed Analytics →
            </Link>
          </div>

          <div className="space-y-3">
            {Object.keys(p.concept_mastery).length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                No concepts assessed yet. Complete a diagnostic knowledge check.
              </p>
            ) : (
              Object.entries(p.concept_mastery).map(([concept, val]) => {
                const pct = Math.round(val * 100);
                const isStrength = p.strengths.includes(concept);
                const isWeak = p.weak_concepts.includes(concept);
                const isUnknown = p.unknown_concepts.includes(concept);

                let badgeLabel = 'Developing';
                let badgeClass = 'bg-slate-100 text-slate-700';
                if (isStrength) {
                  badgeLabel = 'Strength';
                  badgeClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
                } else if (isUnknown) {
                  badgeLabel = 'Missing Knowledge';
                  badgeClass = 'bg-rose-50 text-rose-800 border-rose-200';
                } else if (isWeak) {
                  badgeLabel = 'Weak Attempted';
                  badgeClass = 'bg-amber-50 text-amber-800 border-amber-200';
                }

                return (
                  <div key={concept} className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-800">{concept}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${badgeClass}`}>
                          {badgeLabel}
                        </span>
                        <span className="font-mono font-bold text-slate-700">{pct}%</span>
                      </div>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          pct >= 70 ? 'bg-emerald-500' : pct > 0 ? 'bg-amber-500' : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.max(pct, 4)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Due Spaced Repetitions (1 Column) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-indigo-600" />
              Spaced Repetition
            </h3>
            <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
              {review_queue.length} due
            </span>
          </div>

          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
            {review_queue.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">
                All scheduled repetitions are completed!
              </p>
            ) : (
              review_queue.map((item) => (
                <div key={item.concept} className="p-3 border border-slate-200 rounded-lg space-y-2">
                  <div className="flex items-start justify-between text-xs">
                    <span className="font-semibold text-slate-800">{item.concept}</span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Interval: {item.interval_days}d
                    </span>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      disabled={reviewMutation.isPending}
                      onClick={() =>
                        reviewMutation.mutate({ concept: item.concept, remembered: false })
                      }
                      className="px-2.5 py-1 text-[11px] font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 rounded border border-rose-200 transition-colors inline-flex items-center gap-1"
                    >
                      <XCircle className="w-3 h-3" />
                      Forgot
                    </button>
                    <button
                      type="button"
                      disabled={reviewMutation.isPending}
                      onClick={() =>
                        reviewMutation.mutate({ concept: item.concept, remembered: true })
                      }
                      className="px-2.5 py-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded border border-emerald-200 transition-colors inline-flex items-center gap-1"
                    >
                      <CheckCircle2 className="w-3 h-3" />
                      Remembered
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Personalized Study Plan */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-600" />
            Current Personalized Study Plan
          </h3>
          <Link to="/learning" className="text-xs font-medium text-indigo-600 hover:text-indigo-800">
            Open Study Plan Details →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {study_plan.length === 0 ? (
            <p className="text-xs text-slate-400 col-span-2 py-4 text-center">
              No active study plan items. Generate an assessment to formulate targets.
            </p>
          ) : (
            study_plan.map((item, idx) => (
              <div key={idx} className="p-4 border border-slate-200 rounded-lg bg-slate-50/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-slate-800">{item.title}</span>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${getPriorityBadgeColor(item.priority)}`}>
                    {item.priority}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 leading-relaxed">{item.reason}</p>
                <div className="space-y-1 pt-1">
                  {item.recommended_actions.map((act, actIdx) => (
                    <div key={actIdx} className="flex items-center gap-2 text-[11px] text-slate-700">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                      <span>{act}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

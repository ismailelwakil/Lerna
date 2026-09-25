import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { assessmentsApi } from '../api/assessments';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import {
  AssessmentGenerateResponse,
  AssessmentSubmitResponse,
} from '../api/types';
import { PageHeader } from '../components/layout/PageHeader';
import { MaterialSelector } from '../components/common/MaterialSelector';
import { SourceBadge } from '../components/common/SourceBadge';
import {
  ClipboardCheck,
  CheckCircle,
  Sparkles,
  RotateCcw,
} from 'lucide-react';

export const AssessmentPage: React.FC = () => {
  const { studentId, language, token } = useStudent();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const [topic, setTopic] = useState('Binary Search');
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([]);

  // Assessment flow state
  const [activeAssessment, setActiveAssessment] = useState<AssessmentGenerateResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submissionResult, setSubmissionResult] = useState<AssessmentSubmitResponse | null>(null);

  const generateMutation = useMutation({
    mutationFn: () =>
      assessmentsApi.generate(
        {
          student_id: studentId,
          topic: topic.trim(),
          language: language,
          document_ids: selectedMaterials.length > 0 ? selectedMaterials : null,
        },
        token
      ),
    onSuccess: (res) => {
      // Contract safety check: verify options are not raw file metadata
      const hasMalformedOptions = res.questions.some((q) =>
        q.options.some((opt) => opt.startsWith('Course: ') || opt.startsWith('Topic: Divide-and-Conquer'))
      );

      if (hasMalformedOptions) {
        console.error('Malformed Assessment Contract received:', res);
        addToast({
          type: 'warning',
          title: 'Assessment Contract Notice',
          message: 'The generated question options contain raw text blocks. Rendering safely.',
        });
      }

      setActiveAssessment(res);
      setAnswers({});
      setSubmissionResult(null);
      addToast({
        type: 'success',
        title: 'Assessment Generated',
        message: `Diagnostic knowledge check ready (${res.questions.length} questions).`,
      });
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Generation Failed',
        message: err instanceof Error ? err.message : 'Could not generate knowledge check.',
      });
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!activeAssessment) throw new Error('No active assessment session.');
      return assessmentsApi.submit(
        activeAssessment.assessment_id,
        {
          student_id: studentId,
          answers,
          language: language,
        },
        token
      );
    },
    onSuccess: (res) => {
      setSubmissionResult(res);
      queryClient.invalidateQueries({ queryKey: ['learningState', studentId] });
      queryClient.invalidateQueries({ queryKey: ['studentProfile', studentId] });
      addToast({
        type: 'success',
        title: 'Assessment Evaluated',
        message: `Score: ${Math.round(res.score * 100)}%. Concept mastery updated on server.`,
      });
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Submission Failed',
        message: err instanceof Error ? err.message : 'Could not submit answers.',
      });
    },
  });

  const handleSelectAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleIDontKnow = (questionId: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: "I don't know" }));
  };

  const handleReset = () => {
    setActiveAssessment(null);
    setAnswers({});
    setSubmissionResult(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Diagnostic Knowledge Check & Assessment"
        subtitle="Evaluate conceptual understanding with grounded questions. The backend grades responses and updates student mastery."
      />

      {/* Generation Setup Card (when no assessment active) */}
      {!activeAssessment && !submissionResult && (
        <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              generateMutation.mutate();
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Diagnostic Topic
              </label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Binary Search, Computational Limits..."
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-4 py-2.5 text-xs sm:text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <MaterialSelector
              selectedIds={selectedMaterials}
              onChange={setSelectedMaterials}
            />

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!topic.trim() || generateMutation.isPending}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
              >
                <ClipboardCheck className="w-4 h-4" />
                <span>{generateMutation.isPending ? 'Generating Check...' : 'Start Knowledge Check'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Active Assessment Question Form */}
      {activeAssessment && !submissionResult && (
        <div className="space-y-6">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Knowledge Check: {activeAssessment.topic}
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <SourceBadge sourceType={activeAssessment.source_type} />
                <span className="text-xs text-slate-500 font-mono">
                  {activeAssessment.questions.length} questions
                </span>
              </div>
            </div>

            <button
              onClick={handleReset}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Abandon
            </button>
          </div>

          <div className="space-y-4">
            {activeAssessment.questions.map((q, idx) => {
              const currentAnswer = answers[q.question_id] || '';
              const isIdk = currentAnswer.toLowerCase() === "i don't know";

              return (
                <div key={q.question_id} className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Concept: {q.concept}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleIDontKnow(q.question_id)}
                      className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                        isIdk
                          ? 'bg-amber-100 border-amber-300 text-amber-900 font-semibold'
                          : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      I don't know
                    </button>
                  </div>

                  <p className="text-sm font-medium text-slate-800 leading-relaxed">
                    {q.prompt}
                  </p>

                  {/* Options for MCQ */}
                  {q.options && q.options.length > 0 ? (
                    <div className="space-y-2">
                      {q.options.map((opt, optIdx) => {
                        const isSelected = currentAnswer === opt;
                        return (
                          <div
                            key={optIdx}
                            onClick={() => handleSelectAnswer(q.question_id, opt)}
                            className={`p-3 rounded-lg border text-xs cursor-pointer transition-all flex items-center gap-3 ${
                              isSelected
                                ? 'bg-indigo-50 border-indigo-400 text-indigo-950 font-medium ring-1 ring-indigo-400'
                                : 'bg-slate-50/50 border-slate-200 text-slate-700 hover:bg-slate-100'
                            }`}
                          >
                            <div
                              className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                                isSelected ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300'
                              }`}
                            >
                              {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                            </div>
                            <span>{opt}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div>
                      <input
                        type="text"
                        value={currentAnswer}
                        onChange={(e) => handleSelectAnswer(q.question_id, e.target.value)}
                        placeholder="Type concise answer..."
                        className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex justify-end p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <button
              onClick={() => submitMutation.mutate()}
              disabled={
                Object.keys(answers).length < activeAssessment.questions.length ||
                submitMutation.isPending
              }
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              <CheckCircle className="w-4 h-4" />
              <span>{submitMutation.isPending ? 'Evaluating Answers...' : 'Submit Assessment for Grading'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Submission Results & Feedback View */}
      {submissionResult && (
        <div className="space-y-6">
          <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Diagnostic Result
                </span>
                <h2 className="text-xl font-bold text-slate-900 mt-0.5">
                  Assessment Completed
                </h2>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold font-mono text-indigo-600">
                  {Math.round(submissionResult.score * 100)}%
                </span>
                <span className="block text-[11px] text-slate-400">Mastery Score</span>
              </div>
            </div>

            {/* Recommendations */}
            {submissionResult.recommendations.length > 0 && (
              <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-lg space-y-1.5">
                <h4 className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  Targeted Learning Directives
                </h4>
                <ul className="space-y-1 text-xs text-indigo-800">
                  {submissionResult.recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span>•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Per-Question Server Evaluation */}
          {submissionResult.feedback_per_question && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-900">
                Detailed Evaluation & Rubrics
              </h3>

              {Object.entries(submissionResult.feedback_per_question).map(([qid, fb], i) => (
                <div
                  key={qid}
                  className={`p-4 bg-white rounded-xl border shadow-sm space-y-2 ${
                    fb.is_correct
                      ? 'border-emerald-200'
                      : fb.is_idk
                      ? 'border-amber-200'
                      : 'border-rose-200'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800">
                      Question {i + 1}: {fb.concept}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        fb.is_correct
                          ? 'bg-emerald-100 text-emerald-800'
                          : fb.is_idk
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {fb.is_correct ? 'Correct' : fb.is_idk ? "I Don't Know" : 'Incorrect'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
                    <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Your Answer</span>
                      <span className="font-medium text-slate-800">{fb.student_answer || '(Empty)'}</span>
                    </div>

                    <div className="p-2.5 bg-slate-50 rounded border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Expected / Rubric</span>
                      <span className="font-medium text-slate-800">{fb.expected_answer}</span>
                    </div>
                  </div>

                  {fb.rubric && (
                    <p className="text-[11px] text-slate-500 italic pt-1">
                      Rubric: {fb.rubric}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              Start Another Knowledge Check
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

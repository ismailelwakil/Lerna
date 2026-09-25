import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { studyToolsApi } from '../api/studyTools';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import { GeneratedResource } from '../api/types';
import { PageHeader } from '../components/layout/PageHeader';
import { MaterialSelector } from '../components/common/MaterialSelector';
import { FlashcardViewer } from '../components/study/FlashcardViewer';
import { ArtifactPreview } from '../components/study/ArtifactPreview';
import { QuestionBankViewer } from '../components/study/QuestionBankViewer';
import { EvidenceLimitation } from '../components/common/EvidenceLimitation';
import { SourceBadge } from '../components/common/SourceBadge';
import {
  Sparkles,
  BookOpen,
  FileText,
  HelpCircle,
  Code,
  Image,
  Presentation,
  CheckSquare,
  AlertCircle,
} from 'lucide-react';

export const ALL_STUDY_TOOLS = [
  { id: 'explanation', label: 'Deep Explanation', icon: BookOpen, desc: 'Foundational first-principles explanation' },
  { id: 'summary', label: 'Summary', icon: FileText, desc: 'Executive recap of core mechanics' },
  { id: 'notes', label: 'Study Notes', icon: FileText, desc: 'Structured bulleted revision notes' },
  { id: 'study_guide', label: 'Study Guide', icon: BookOpen, desc: 'Comprehensive roadmap with objectives' },
  { id: 'flashcards', label: 'Flashcards', icon: Sparkles, desc: 'Q&A revision flashcards with rubrics' },
  { id: 'quiz', label: 'Practice Quiz', icon: HelpCircle, desc: 'Formative multiple-choice questions' },
  { id: 'exam', label: 'Formal Exam', icon: CheckSquare, desc: 'Academic examination questions & grading keys' },
  { id: 'practice', label: 'Problem Set', icon: CheckSquare, desc: 'Worked problems & exercises' },
  { id: 'code', label: 'Code Example', icon: Code, desc: 'Implementation with edge cases' },
  { id: 'coding_exercise', label: 'Coding Exercise', icon: Code, desc: 'Coding problem specification & test harness' },
  { id: 'diagram', label: 'Diagram (SVG)', icon: Image, desc: 'Scalable vector visual diagram (.svg)' },
  { id: 'presentation', label: 'Presentation (PPTX)', icon: Presentation, desc: 'PowerPoint slide deck (.pptx)' },
  { id: 'analogy', label: 'Analogy', icon: Sparkles, desc: 'Grounded real-world analogy' },
  { id: 'comparison', label: 'Comparative Table', icon: FileText, desc: 'Matrix contrasting trade-offs' },
  { id: 'question_bank', label: 'Question Bank', icon: HelpCircle, desc: 'Exhaustive repository of questions & rubrics' },
] as const;

export const StudyToolsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { studentId, language, token } = useStudent();
  const { addToast } = useToast();

  const initialTopic = searchParams.get('topic') || 'Binary Search';
  const initialTool = searchParams.get('tool');

  const [topic, setTopic] = useState(initialTopic);
  const [selectedTools, setSelectedTools] = useState<string[]>(
    initialTool ? [initialTool] : ['explanation', 'flashcards']
  );
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([]);
  const [generatedResults, setGeneratedResults] = useState<Record<string, GeneratedResource>>({});
  const [activeTab, setActiveTab] = useState<string>('explanation');

  const toggleTool = (toolId: string) => {
    if (selectedTools.includes(toolId)) {
      if (selectedTools.length > 1) {
        setSelectedTools(selectedTools.filter((t) => t !== toolId));
      }
    } else {
      setSelectedTools([...selectedTools, toolId]);
    }
  };

  const selectAllTools = () => {
    setSelectedTools(ALL_STUDY_TOOLS.map((t) => t.id));
  };

  const generateMutation = useMutation({
    mutationFn: () =>
      studyToolsApi.generate(
        {
          student_id: studentId,
          topic: topic.trim(),
          kinds: selectedTools,
          language: language,
          document_ids: selectedMaterials.length > 0 ? selectedMaterials : null,
        },
        token
      ),
    onSuccess: (res) => {
      setGeneratedResults(res.resources);
      const firstAvailable = Object.keys(res.resources)[0];
      if (firstAvailable) {
        setActiveTab(firstAvailable);
      }
      addToast({
        type: 'success',
        title: 'Study Tools Generated',
        message: `Successfully created ${Object.keys(res.resources).length} grounded learning resource(s).`,
      });
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Generation Failed',
        message: err instanceof Error ? err.message : 'Could not generate study tools.',
      });
    },
  });

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || generateMutation.isPending) return;
    generateMutation.mutate();
  };

  const activeResource = generatedResults[activeTab];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Academic Study Tools & Content Generation"
        subtitle="Generate 15 verified pedagogical resources grounded in course materials or authoritative university sources."
      />

      {/* Control Configuration Card */}
      <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-5">
        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Topic or Lecture Concept
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Binary Search, Depth First Search, Dynamic Programming..."
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-4 py-2.5 text-xs sm:text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <MaterialSelector
            selectedIds={selectedMaterials}
            onChange={setSelectedMaterials}
          />

          {/* Multi-Select Tools Grid */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-slate-700">
                Select Study Tool Kinds ({selectedTools.length} selected)
              </label>
              <button
                type="button"
                onClick={selectAllTools}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Select All 15 Tools
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 max-h-56 overflow-y-auto p-1 border border-slate-200 rounded-xl bg-slate-50/50">
              {ALL_STUDY_TOOLS.map((tool) => {
                const isSelected = selectedTools.includes(tool.id);
                const Icon = tool.icon;
                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={() => toggleTool(tool.id)}
                    className={`p-2.5 rounded-lg border text-left flex items-start gap-2 transition-all ${
                      isSelected
                        ? 'bg-indigo-50 border-indigo-400 text-indigo-950 shadow-xs font-semibold'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                        isSelected ? 'text-indigo-600' : 'text-slate-400'
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="text-xs truncate">{tool.label}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={!topic.trim() || generateMutation.isPending}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              <span>{generateMutation.isPending ? 'Generating Tools...' : 'Generate Selected Tools'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Generated Resources Output Area */}
      {Object.keys(generatedResults).length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-4">
          {/* Navigation Tabs */}
          <div className="border-b border-slate-200 bg-slate-50 flex items-center overflow-x-auto px-4 pt-2 gap-1">
            {Object.entries(generatedResults).map(([kind, res]) => (
              <button
                key={kind}
                onClick={() => setActiveTab(kind)}
                className={`px-4 py-2.5 text-xs font-medium border-b-2 whitespace-nowrap transition-colors flex items-center gap-2 ${
                  activeTab === kind
                    ? 'border-indigo-600 text-indigo-700 bg-white rounded-t-lg'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>{ALL_STUDY_TOOLS.find((t) => t.id === kind)?.label || kind}</span>
                {res.type === 'unavailable' && (
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                )}
              </button>
            ))}
          </div>

          {/* Active Tool Content */}
          {activeResource && (
            <div className="p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <SourceBadge sourceType={activeResource.source_type} />
                  {activeResource.learner_state && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                      State: {activeResource.learner_state}
                    </span>
                  )}
                  {activeResource.teaching_strategy && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700">
                      Strategy: {activeResource.teaching_strategy}
                    </span>
                  )}
                </div>

                {activeResource.sources.length > 0 && (
                  <div className="text-xs text-slate-500">
                    Grounded in {activeResource.sources.length} source(s)
                  </div>
                )}
              </div>

              {/* Evidence Limitation Callout */}
              {activeResource.evidence_limitation && (
                <EvidenceLimitation message={activeResource.evidence_limitation} />
              )}

              {/* Unavailable State */}
              {activeResource.type === 'unavailable' ? (
                <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-2">
                  <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
                  <h4 className="text-sm font-semibold text-rose-900">
                    Resource Unavailable Without Speculation
                  </h4>
                  <p className="text-xs text-rose-700 max-w-md mx-auto">
                    {activeResource.message ||
                      'Trusted evidence is unavailable or insufficient, so this resource was not generated from model memory.'}
                  </p>
                </div>
              ) : activeResource.kind === 'flashcards' && activeResource.content ? (
                <FlashcardViewer content={activeResource.content} />
              ) : activeResource.type === 'file' || activeResource.path ? (
                <ArtifactPreview resource={activeResource} />
              ) : ['exam', 'quiz', 'practice', 'question_bank'].includes(activeResource.kind) &&
                activeResource.content ? (
                <QuestionBankViewer content={activeResource.content} />
              ) : (
                <div className="prose prose-sm max-w-none text-slate-800 leading-relaxed whitespace-pre-wrap font-sans bg-slate-50/50 p-6 rounded-xl border border-slate-100">
                  {activeResource.content}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

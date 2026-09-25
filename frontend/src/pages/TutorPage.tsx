import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { tutorApi } from '../api/tutor';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import { TutorChatResponse, Citation } from '../api/types';
import { MaterialSelector } from '../components/common/MaterialSelector';
import { CitationCard } from '../components/common/CitationCard';
import { EvidenceLimitation } from '../components/common/EvidenceLimitation';
import {
  Send,
  Sparkles,
  ShieldAlert,
  RotateCcw,
  BookOpen,
  User,
  Bot,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  evidence?: Citation[];
  abstained?: boolean;
  evidenceLimitation?: string | null;
  sourceType?: string;
  timestamp: string;
}

export const TutorPage: React.FC = () => {
  const { studentId, profile, language, token } = useStudent();
  const { addToast } = useToast();

  const [inputQuery, setInputQuery] = useState('');
  const [tutoringStyle, setTutoringStyle] = useState<'direct' | 'socratic'>('direct');
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello ${profile?.name || 'Scholar'}! I am your AI Academic Tutor. Every factual response is grounded strictly in your course materials or verified university lecture notes. How can I help you today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (text: string) =>
      tutorApi.chat(
        {
          student_id: studentId,
          course_id: profile?.course || 'General',
          message: text,
          language: language,
          document_ids: selectedMaterialIds.length > 0 ? selectedMaterialIds : null,
          tutoring_style: tutoringStyle,
          session_id: 'web-session',
          chat_history: messages.slice(-4).map((m) => ({ role: m.role, content: m.content })),
        },
        token
      ),
    onSuccess: (res: TutorChatResponse) => {
      const assistantMsg: ChatMessage = {
        id: `${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        evidence: res.evidence,
        abstained: res.abstained,
        evidenceLimitation: res.evidence_limitation,
        sourceType: res.source_type,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Tutor Query Failed',
        message: err instanceof Error ? err.message : 'Could not contact AI Tutor.',
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = inputQuery.trim();
    if (!query || chatMutation.isPending) return;

    const userMsg: ChatMessage = {
      id: `${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    chatMutation.mutate(query);
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        role: 'assistant',
        content: 'Conversation cleared. What topic or concept would you like to explore next?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Sample prompt helper
  const handleSamplePrompt = (sampleText: string) => {
    setInputQuery(sampleText);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] space-y-4">
      {/* Header with Scope Controls */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3 flex-shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Bot className="w-5 h-5 text-indigo-600" />
              AI Academic Tutor
            </h1>
            <p className="text-xs text-slate-500">
              Grounded, citation-backed conversational learning with hierarchical personalization.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Style Selector */}
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setTutoringStyle('direct')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  tutoringStyle === 'direct'
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Direct Explanation
              </button>
              <button
                type="button"
                onClick={() => setTutoringStyle('socratic')}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                  tutoringStyle === 'socratic'
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Socratic Guidance
              </button>
            </div>

            <button
              type="button"
              onClick={handleClearChat}
              title="Clear conversation"
              className="p-1.5 text-slate-400 hover:text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Material Selection / Grounding Scope */}
        <MaterialSelector
          selectedIds={selectedMaterialIds}
          onChange={setSelectedMaterialIds}
        />
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm p-4 overflow-y-auto space-y-4">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  isUser
                    ? 'bg-indigo-600 text-white'
                    : 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                }`}
              >
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-3xl rounded-2xl p-4 text-xs sm:text-sm leading-relaxed space-y-3 ${
                  isUser
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-none'
                }`}
              >
                {/* Safe Refusal Callout */}
                {msg.abstained && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-900 text-xs flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
                    <span>
                      Authoritative evidence was insufficient to answer with verified accuracy. The tutor will not speculate from ungrounded memory.
                    </span>
                  </div>
                )}

                {/* Evidence Limitation Callout */}
                {msg.evidenceLimitation && (
                  <EvidenceLimitation message={msg.evidenceLimitation} />
                )}

                {/* Message Body */}
                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                {/* Used Citations & Sources (if present) */}
                {msg.evidence && msg.evidence.length > 0 && !isUser && (
                  <div className="pt-3 border-t border-slate-200/80 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold">
                      <span className="flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
                        Grounded Sources & Citations ({msg.evidence.length})
                      </span>
                    </div>

                    <div className="space-y-1.5">
                      {msg.evidence.map((cite, idx) => (
                        <CitationCard key={idx} citation={cite} index={idx} />
                      ))}
                    </div>
                  </div>
                )}

                <div
                  className={`text-[10px] ${
                    isUser ? 'text-indigo-200 text-right' : 'text-slate-400'
                  }`}
                >
                  {msg.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {chatMutation.isPending && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200 flex items-center justify-center">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-2xl rounded-tl-none space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600 animate-spin" />
                <span>Searching trusted sources & formulating grounded explanation...</span>
              </div>
              <div className="w-48 h-2 bg-slate-200 rounded animate-pulse" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form & Suggestions */}
      <div className="space-y-2 flex-shrink-0">
        {messages.length <= 2 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
            <span className="text-slate-400 text-[11px] whitespace-nowrap">Suggested prompts:</span>
            <button
              onClick={() =>
                handleSamplePrompt(
                  'Explain how binary search works, including its required input condition, decision process, worst-case time complexity, and iterative space complexity.'
                )
              }
              className="px-2.5 py-1 bg-white hover:bg-slate-50 text-indigo-700 border border-indigo-200 rounded-full whitespace-nowrap transition-colors"
            >
              Binary search mechanics & complexity
            </button>
            <button
              onClick={() =>
                handleSamplePrompt('Why is the worst-case time complexity of binary search O(log n)?')
              }
              className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-full whitespace-nowrap transition-colors"
            >
              Derivation of O(log n)
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={chatMutation.isPending}
            placeholder="Ask an academic question (e.g., 'Explain binary search decision process and O(log n) worst-case bound')..."
            className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-sm"
          />

          <button
            type="submit"
            disabled={!inputQuery.trim() || chatMutation.isPending}
            className="px-4 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl font-medium text-xs sm:text-sm flex items-center gap-2 shadow-sm transition-colors"
          >
            <span>Send</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

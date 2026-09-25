import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { materialsApi } from '../api/materials';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import { PageHeader } from '../components/layout/PageHeader';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  UploadCloud,
  FileText,
  FileCode,
  FolderOpen,
  ArrowRight,
} from 'lucide-react';

export const MaterialsPage: React.FC = () => {
  const { studentId, profile, token } = useStudent();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [courseName, setCourseName] = useState<string>(profile?.course || 'General');

  const { data: materialsData, isLoading, error, refetch } = useQuery({
    queryKey: ['materials', studentId, profile?.course],
    queryFn: () => materialsApi.listMaterials(studentId, profile?.course, token),
    staleTime: 1000 * 60 * 2,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      materialsApi.uploadMaterial(file, courseName, studentId, token),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['materials', studentId] });
      setSelectedFile(null);
      addToast({
        type: 'success',
        title: 'Upload Successful',
        message: `${res.filename} indexed (${res.chunk_count} chunks) into Chroma vector store.`,
      });
    },
    onError: (err) => {
      addToast({
        type: 'error',
        title: 'Upload Failed',
        message: err instanceof Error ? err.message : 'Could not upload document.',
      });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    uploadMutation.mutate(selectedFile);
  };

  const materials = materialsData?.materials || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Course Materials & Grounding Documents"
        subtitle="Upload textbooks, lecture transcripts, and slide decks to create source-constrained learning environments."
      />

      {/* Upload Zone */}
      <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-indigo-600" />
          Ingest New Learning Material
        </h3>

        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Course
              </label>
              <input
                type="text"
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                placeholder="e.g. Computer Science, Algorithms..."
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Supported Formats
              </label>
              <div className="text-xs text-slate-500 py-2">
                .txt, .md, .pdf (via pypdf), .docx, .pptx
              </div>
            </div>
          </div>

          <div className="border-2 border-dashed border-slate-300 hover:border-indigo-400 rounded-xl p-6 text-center transition-colors">
            <input
              type="file"
              id="file-upload"
              accept=".txt,.md,.pdf,.docx,.pptx"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
              <FileCode className="w-8 h-8 text-indigo-500 mx-auto" />
              <div className="text-xs font-semibold text-slate-800">
                {selectedFile ? selectedFile.name : 'Click to select or drop document'}
              </div>
              <div className="text-[11px] text-slate-500">
                {selectedFile
                  ? `${Math.round(selectedFile.size / 1024)} KB · Ready to ingest`
                  : 'Files are chunked, embedded with multilingual-e5-small, and indexed into ChromaDB'}
              </div>
            </label>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{uploadMutation.isPending ? 'Ingesting & Indexing...' : 'Upload & Index'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Materials List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-indigo-600" />
            Indexed Course Documents ({materials.length})
          </h3>
          <span className="text-xs text-slate-500">
            Vector Store: ChromaDB (Collection: academic_knowledge)
          </span>
        </div>

        {isLoading ? (
          <LoadingState message="Loading indexed documents..." />
        ) : error ? (
          <div className="p-6">
            <ErrorState message={error instanceof Error ? error.message : 'Failed to load materials.'} onRetry={refetch} />
          </div>
        ) : materials.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No materials uploaded yet"
              description="Upload your lecture notes or textbooks above to ground the AI Tutor in your curriculum."
            />
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {materials.map((mat) => (
              <div key={mat.document_id} className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:bg-slate-50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 flex-shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs sm:text-sm font-semibold text-slate-800">{mat.filename}</h4>
                    <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                      <span>Course: {mat.course}</span>
                      <span>·</span>
                      <span>{mat.chunk_count} chunk(s)</span>
                      <span>·</span>
                      <span className="font-mono text-[10px] text-slate-400">{mat.document_id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <StatusBadge status={mat.status} label="Indexed in Vector DB" />
                  <Link
                    to={`/tutor`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    Use with Tutor
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

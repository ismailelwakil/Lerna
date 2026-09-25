import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { StudyToolsGenerateRequest, StudyToolsGenerateResponse } from './types';

export const studyToolsApi = {
  generate: (data: StudyToolsGenerateRequest, token?: string | null) =>
    apiClient<StudyToolsGenerateResponse>(ENDPOINTS.STUDY_TOOLS_GENERATE, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
      studentId: data.student_id,
    }),

  getArtifactDownloadUrl: (artifactId: string) => {
    const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
    return `${base}${ENDPOINTS.ARTIFACT_DOWNLOAD(artifactId)}`;
  },
};

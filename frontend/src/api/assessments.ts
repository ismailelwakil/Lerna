import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import {
  AssessmentGenerateRequest,
  AssessmentGenerateResponse,
  AssessmentSubmitRequest,
  AssessmentSubmitResponse,
} from './types';

export const assessmentsApi = {
  generate: (data: AssessmentGenerateRequest, token?: string | null) =>
    apiClient<AssessmentGenerateResponse>(ENDPOINTS.ASSESSMENTS_GENERATE, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
      studentId: data.student_id,
    }),

  submit: (
    assessmentId: string,
    data: AssessmentSubmitRequest,
    token?: string | null
  ) =>
    apiClient<AssessmentSubmitResponse>(ENDPOINTS.ASSESSMENTS_SUBMIT(assessmentId), {
      method: 'POST',
      body: JSON.stringify(data),
      token,
      studentId: data.student_id,
    }),
};

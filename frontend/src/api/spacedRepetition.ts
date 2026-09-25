import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { SpacedReviewRequest, SpacedReviewResponse } from './types';

export const spacedRepetitionApi = {
  recordReview: (data: SpacedReviewRequest, token?: string | null) =>
    apiClient<SpacedReviewResponse>(ENDPOINTS.SPACED_REPETITION_REVIEW, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
      studentId: data.student_id,
    }),
};

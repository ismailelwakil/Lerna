import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { TutorChatRequest, TutorChatResponse } from './types';

export const tutorApi = {
  chat: (data: TutorChatRequest, token?: string | null) =>
    apiClient<TutorChatResponse>(ENDPOINTS.TUTOR_CHAT, {
      method: 'POST',
      body: JSON.stringify(data),
      token,
      studentId: data.student_id,
    }),

  sendVoiceQuestion: (formData: FormData, token?: string | null) =>
    apiClient<TutorChatResponse>(ENDPOINTS.TUTOR_VOICE, {
      method: 'POST',
      body: formData,
      token,
    }),
};

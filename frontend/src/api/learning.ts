import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { LearningState, SystemCapabilities, HealthStatus } from './types';

export const learningApi = {
  getLearningState: (studentId: string, token?: string | null) =>
    apiClient<LearningState>(ENDPOINTS.LEARNING(studentId), { token, studentId }),

  getCapabilities: (token?: string | null) =>
    apiClient<SystemCapabilities>(ENDPOINTS.CAPABILITIES, { token }),

  getHealth: () =>
    apiClient<HealthStatus>(ENDPOINTS.HEALTH),
};

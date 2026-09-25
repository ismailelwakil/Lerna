import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { StudentProfile, StudentPreferencesUpdate } from './types';

export const profileApi = {
  getProfile: (studentId: string, token?: string | null) =>
    apiClient<StudentProfile>(ENDPOINTS.PROFILE(studentId), { token, studentId }),

  updatePreferences: (
    studentId: string,
    updates: StudentPreferencesUpdate,
    token?: string | null
  ) =>
    apiClient<StudentProfile>(ENDPOINTS.PREFERENCES(studentId), {
      method: 'PATCH',
      body: JSON.stringify(updates),
      token,
      studentId,
    }),
};

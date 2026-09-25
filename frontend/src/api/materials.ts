import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';
import { MaterialsListResponse, MaterialUploadResponse } from './types';

export const materialsApi = {
  listMaterials: (studentId: string, course?: string, token?: string | null) => {
    const params = new URLSearchParams({ student_id: studentId });
    if (course) params.append('course', course);
    return apiClient<MaterialsListResponse>(`${ENDPOINTS.MATERIALS}?${params.toString()}`, {
      token,
      studentId,
    });
  },

  uploadMaterial: (
    file: File,
    course: string,
    studentId: string,
    token?: string | null
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('course', course);
    formData.append('student_id', studentId);

    return apiClient<MaterialUploadResponse>(ENDPOINTS.MATERIALS_UPLOAD, {
      method: 'POST',
      body: formData,
      token,
      studentId,
    });
  },
};

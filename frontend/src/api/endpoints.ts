/**
 * API Endpoints Constants
 */
export const ENDPOINTS = {
  HEALTH: '/health',
  CAPABILITIES: '/capabilities',
  PROFILE: (studentId: string) => `/students/${encodeURIComponent(studentId)}/profile`,
  PREFERENCES: (studentId: string) => `/students/${encodeURIComponent(studentId)}/preferences`,
  LEARNING: (studentId: string) => `/students/${encodeURIComponent(studentId)}/learning`,
  TUTOR_CHAT: '/tutor/chat',
  TUTOR_VOICE: '/tutor/voice',
  MATERIALS: '/materials',
  MATERIALS_UPLOAD: '/materials/upload',
  STUDY_TOOLS_GENERATE: '/study-tools/generate',
  ASSESSMENTS_GENERATE: '/assessments/generate',
  ASSESSMENTS_SUBMIT: (assessmentId: string) => `/assessments/${encodeURIComponent(assessmentId)}/submit`,
  SPACED_REPETITION_REVIEW: '/spaced-repetition/review',
  ARTIFACT_DOWNLOAD: (artifactId: string) => `/artifacts/${encodeURIComponent(artifactId)}/download`,
} as const;

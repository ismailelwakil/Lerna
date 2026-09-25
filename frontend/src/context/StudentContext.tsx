import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { profileApi } from '../api/profile';
import { StudentProfile, StudentPreferencesUpdate } from '../api/types';

interface StudentContextType {
  studentId: string;
  setStudentId: (id: string) => void;
  token: string | null;
  setToken: (token: string | null) => void;
  profile: StudentProfile | null;
  isLoading: boolean;
  error: Error | null;
  updatePreferences: (updates: StudentPreferencesUpdate) => Promise<StudentProfile>;
  isUpdating: boolean;
  language: string;
  setLanguage: (lang: string) => void;
  isRtl: boolean;
}

const StudentContext = createContext<StudentContextType | undefined>(undefined);

export const StudentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();

  // Active student identity: defaults to env variable or fallback 'student-001'
  const defaultStudentId = import.meta.env.VITE_DEMO_STUDENT_ID || 'student-001';
  const [studentId, setStudentIdState] = useState<string>(() => {
    return localStorage.getItem('academic_os_student_id') || defaultStudentId;
  });

  // Future JWT / Bearer token storage abstraction
  const [token, setTokenState] = useState<string | null>(() => {
    return localStorage.getItem('academic_os_auth_token') || null;
  });

  const setStudentId = (id: string) => {
    const cleanId = id.trim() || defaultStudentId;
    setStudentIdState(cleanId);
    localStorage.setItem('academic_os_student_id', cleanId);
  };

  const setToken = (newToken: string | null) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem('academic_os_auth_token', newToken);
    } else {
      localStorage.removeItem('academic_os_auth_token');
    }
  };

  // Fetch active student profile from backend
  const {
    data: profile,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['studentProfile', studentId],
    queryFn: () => profileApi.getProfile(studentId, token),
    staleTime: 1000 * 60 * 2,
    retry: 1,
  });

  const [language, setLanguageState] = useState<string>('en');

  useEffect(() => {
    if (profile?.preferred_language) {
      setLanguageState(profile.preferred_language);
    }
  }, [profile?.preferred_language]);

  const updateMutation = useMutation({
    mutationFn: (updates: StudentPreferencesUpdate) =>
      profileApi.updatePreferences(studentId, updates, token),
    onSuccess: (updated) => {
      queryClient.setQueryData(['studentProfile', studentId], updated);
      queryClient.invalidateQueries({ queryKey: ['learningState', studentId] });
      if (updated.preferred_language) {
        setLanguageState(updated.preferred_language);
      }
    },
  });

  const setLanguage = (lang: string) => {
    setLanguageState(lang);
    if (profile && profile.preferred_language !== lang) {
      updateMutation.mutate({ preferred_language: lang });
    }
  };

  const isRtl = language === 'ar';

  return (
    <StudentContext.Provider
      value={{
        studentId,
        setStudentId,
        token,
        setToken,
        profile: profile || null,
        isLoading,
        error: error instanceof Error ? error : null,
        updatePreferences: updateMutation.mutateAsync,
        isUpdating: updateMutation.isPending,
        language,
        setLanguage,
        isRtl,
      }}
    >
      <div dir={isRtl ? 'rtl' : 'ltr'}>{children}</div>
    </StudentContext.Provider>
  );
};

export const useStudent = () => {
  const context = useContext(StudentContext);
  if (!context) {
    throw new Error('useStudent must be used within a StudentProvider');
  }
  return context;
};

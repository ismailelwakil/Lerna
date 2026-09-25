import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StudentProvider } from './context/StudentContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';

// Pages
import { Dashboard } from './pages/Dashboard';
import { TutorPage } from './pages/TutorPage';
import { MyLearningPage } from './pages/MyLearningPage';
import { MaterialsPage } from './pages/MaterialsPage';
import { StudyToolsPage } from './pages/StudyToolsPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { ProfilePage } from './pages/ProfilePage';
import { SystemPage } from './pages/SystemPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <StudentProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppShell />}>
                <Route index element={<Dashboard />} />
                <Route path="tutor" element={<TutorPage />} />
                <Route path="learning" element={<MyLearningPage />} />
                <Route path="materials" element={<MaterialsPage />} />
                <Route path="study-tools" element={<StudyToolsPage />} />
                <Route path="assessment" element={<AssessmentPage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="system" element={<SystemPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </StudentProvider>
    </QueryClientProvider>
  );
};

export default App;

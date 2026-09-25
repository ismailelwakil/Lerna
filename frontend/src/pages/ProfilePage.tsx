import React, { useState, useEffect } from 'react';
import { useStudent } from '../context/StudentContext';
import { useToast } from '../context/ToastContext';
import { PageHeader } from '../components/layout/PageHeader';
import { LearningPreferenceSelector } from '../components/common/LearningPreferenceSelector';
import { LanguageSelector } from '../components/common/LanguageSelector';
import { User, Save } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { studentId, profile, updatePreferences, isUpdating } = useStudent();
  const { addToast } = useToast();

  const [name, setName] = useState(profile?.name || 'Demo Student');
  const [course, setCourse] = useState(profile?.course || 'Artificial Intelligence');
  const [preference, setPreference] = useState(profile?.learning_preference || 'step-by-step');

  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setCourse(profile.course);
      setPreference(profile.learning_preference);
    }
  }, [profile]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updatePreferences({
        name,
        course,
        learning_preference: preference,
      });
      addToast({
        type: 'success',
        title: 'Preferences Updated',
        message: 'Your learner profile context was saved to backend storage.',
      });
    } catch (err) {
      addToast({
        type: 'error',
        title: 'Update Failed',
        message: err instanceof Error ? err.message : 'Could not save preferences.',
      });
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title="Student Profile & Pedagogical Preferences"
        subtitle="Configure your learner identity, active academic course, and teaching strategy preferences."
      />

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Readonly Identity Banner */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-indigo-100 border border-indigo-300 flex items-center justify-center text-indigo-700 font-bold text-sm">
                <User className="w-5 h-5" />
              </div>
              <div>
                <span className="font-semibold text-slate-800 block text-sm">
                  {name || 'Demo Student'}
                </span>
                <span className="text-slate-500 font-mono text-[11px]">
                  Student Identity ID: {studentId}
                </span>
              </div>
            </div>
            <span className="px-2.5 py-1 rounded bg-indigo-50 border border-indigo-200 text-indigo-700 font-medium">
              Persisted Profile
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Active Course / Curriculum
              </label>
              <input
                type="text"
                value={course}
                onChange={(e) => setCourse(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Learning Preference Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Pedagogical Preference & Tutoring Strategy
            </label>
            <LearningPreferenceSelector
              value={preference}
              onChange={setPreference}
            />
          </div>

          {/* Language Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Default Learning Language
            </label>
            <LanguageSelector />
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-100">
            <button
              type="submit"
              disabled={isUpdating}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              <Save className="w-4 h-4" />
              <span>{isUpdating ? 'Saving Preferences...' : 'Save Profile Preferences'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

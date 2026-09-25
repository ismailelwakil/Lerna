/**
 * Frontend UI Localization (i18n)
 * Supports all backend language codes: en, ar, fr, sw, ha, am, so, yo, ig, zu
 */

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', native: 'English', rtl: false },
  { code: 'ar', name: 'Arabic', native: 'العربية', rtl: true },
  { code: 'fr', name: 'French', native: 'Français', rtl: false },
  { code: 'sw', name: 'Swahili', native: 'Kiswahili', rtl: false },
  { code: 'ha', name: 'Hausa', native: 'Hausa', rtl: false },
  { code: 'am', name: 'Amharic', native: 'አማርኛ', rtl: false },
  { code: 'so', name: 'Somali', native: 'Soomaali', rtl: false },
  { code: 'yo', name: 'Yoruba', native: 'Èdè Yorùbá', rtl: false },
  { code: 'ig', name: 'Igbo', native: 'Asụsụ Igbo', rtl: false },
  { code: 'zu', name: 'Zulu', native: 'isiZulu', rtl: false },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]['code'];

export const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: {
    // Nav
    nav_dashboard: 'Dashboard',
    nav_tutor: 'AI Tutor',
    nav_learning: 'My Learning',
    nav_materials: 'Course Materials',
    nav_study_tools: 'Study Tools',
    nav_assessment: 'Knowledge Check',
    nav_profile: 'Student Profile',
    nav_system: 'System Status',

    // Common
    loading: 'Loading...',
    save: 'Save Changes',
    cancel: 'Cancel',
    submit: 'Submit',
    generate: 'Generate',
    retry: 'Retry',
    search: 'Search',
    all_course_materials: 'All course materials (Trusted External Search)',
    selected_materials: 'Selected course materials',
    mode_trusted_external: 'Trusted External Mode',
    mode_upload: 'Course Material Mode',
    error_title: 'An error occurred',
    empty_title: 'No items to display',
    refresh: 'Refresh',

    // Tutor
    tutor_title: 'AI Academic Tutor',
    tutor_subtitle: 'Ask conceptual questions grounded strictly in course materials or authoritative university sources.',
    style_direct: 'Direct Explanation',
    style_socratic: 'Socratic Guidance',
    send_message: 'Send question',
    ask_placeholder: 'Ask an academic or conceptual question...',
    sources_used: 'Sources & Citations',
    evidence_limitation: 'Evidence Limitation Notice',
    safe_refusal: 'Safe Refusal',
    voice_input: 'Voice Question',

    // Study Tools
    study_tools_title: 'Academic Study Tools',
    study_tools_subtitle: 'Generate 15 grounded learning resources tailored to your mastery profile.',
    enter_topic: 'Enter concept or lecture topic...',
    select_tools: 'Select study tools to generate',

    // Assessment
    assessment_title: 'Diagnostic Knowledge Check',
    assessment_subtitle: 'Evaluate your understanding with grounded questions and receive targeted mastery feedback.',
    start_assessment: 'Generate Knowledge Check',
    i_dont_know: "I don't know",
    score_label: 'Final Assessment Score',

    // Dashboard
    welcome_back: 'Welcome back',
    next_best_action: 'Recommended Next Action',
    mastery_overview: 'Concept Mastery Overview',
    due_reviews: 'Due Spaced Repetitions',
    study_plan_progress: 'Personalized Study Plan',
  },
  ar: {
    nav_dashboard: 'لوحة التحكم',
    nav_tutor: 'المعلم الذكي',
    nav_learning: 'مساري التعليمي',
    nav_materials: 'المقررات الدراسية',
    nav_study_tools: 'أدوات الدراسة',
    nav_assessment: 'تقييم المعرفة',
    nav_profile: 'الملف الشخصي',
    nav_system: 'حالة النظام',

    loading: 'جاري التحميل...',
    save: 'حفظ التغييرات',
    cancel: 'إلغاء',
    submit: 'إرسال',
    generate: 'توليد',
    retry: 'إعادة المحاولة',
    search: 'بحث',
    all_course_materials: 'جميع المواد الدراسية (بحث خارجي موثوق)',
    selected_materials: 'المواد الدراسية المحددة',
    mode_trusted_external: 'وضع البحث الخارجي الموثوق',
    mode_upload: 'وضع مواد المقرر',
    error_title: 'حدث خطأ',
    empty_title: 'لا توجد بيانات للعرض',
    refresh: 'تحديث',

    tutor_title: 'المعلم الأكاديمي الذكي',
    tutor_subtitle: 'اطرح أسئلة مفاهيمية مبنية حصرياً على مواد مقررك أو مصادر جامعية موثوقة.',
    style_direct: 'شرح مباشر',
    style_socratic: 'توجيه سقراطي',
    send_message: 'إرسال السؤال',
    ask_placeholder: 'اطرح سؤالاً أكاديمياً أو مفهومياً...',
    sources_used: 'المصادر والاستشهادات',
    evidence_limitation: 'ملاحظة حدود الأدلة',
    safe_refusal: 'امتناع آمن',
    voice_input: 'سؤال صوتي',

    study_tools_title: 'أدوات الدراسة الأكاديمية',
    study_tools_subtitle: 'توليد 15 مورداً تعليمياً موثقاً ومخصصاً لمستوى تمكنك.',
    enter_topic: 'أدخل المفهوم أو موضوع المحاضرة...',
    select_tools: 'حدد أدوات الدراسة المطلوبة',

    assessment_title: 'تقييم المعرفة التشخيصي',
    assessment_subtitle: 'قيّم فهمك بأسئلة موثقة واحصل على تقييم فوري لمستوى تمكنك.',
    start_assessment: 'بدء التقييم',
    i_dont_know: 'لا أعرف',
    score_label: 'درجة التقييم النهائية',

    welcome_back: 'مرحباً بك',
    next_best_action: 'الإجراء التعليمي الموصى به',
    mastery_overview: 'نظرة عامة على تمكن المفاهيم',
    due_reviews: 'مراجعات التكرار المتباعد المستحقة',
    study_plan_progress: 'خطة الدراسة المخصصة',
  },
  fr: {
    nav_dashboard: 'Tableau de bord',
    nav_tutor: 'Tuteur IA',
    nav_learning: 'Mon Apprentissage',
    nav_materials: 'Documents de cours',
    nav_study_tools: "Outils d'étude",
    nav_assessment: 'Évaluation',
    nav_profile: 'Profil étudiant',
    nav_system: 'État du système',

    loading: 'Chargement...',
    save: 'Enregistrer',
    cancel: 'Annuler',
    submit: 'Soumettre',
    generate: 'Générer',
    retry: 'Réessayer',
    search: 'Rechercher',
    all_course_materials: 'Tous les cours (Recherche externe de confiance)',
    selected_materials: 'Documents sélectionnés',
    mode_trusted_external: 'Mode Externe de Confiance',
    mode_upload: 'Mode Documents Importés',
    error_title: 'Une erreur est survenue',
    empty_title: 'Aucun élément',
    refresh: 'Actualiser',

    tutor_title: 'Tuteur Académique IA',
    tutor_subtitle: 'Posez des questions conceptuelles fondées sur vos cours ou des sources universitaires fiables.',
    style_direct: 'Explication directe',
    style_socratic: 'Guidance socratique',
    send_message: 'Envoyer',
    ask_placeholder: 'Posez une question académique ou conceptuelle...',
    sources_used: 'Sources et citations',
    evidence_limitation: 'Avis de limitation des preuves',
    safe_refusal: 'Refus sécurisé',
    voice_input: 'Question vocale',

    study_tools_title: "Outils d'Étude Académiques",
    study_tools_subtitle: 'Générez 15 ressources pédagogiques vérifiées et adaptées à votre profil.',
    enter_topic: 'Saisissez le sujet ou le concept...',
    select_tools: "Sélectionnez les outils d'étude",

    assessment_title: 'Évaluation Diagnostique',
    assessment_subtitle: 'Évaluez vos compétences avec des questions sourcées.',
    start_assessment: "Lancer l'évaluation",
    i_dont_know: 'Je ne sais pas',
    score_label: 'Score final',

    welcome_back: 'Bienvenue',
    next_best_action: 'Action suivante recommandée',
    mastery_overview: 'Aperçu de la maîtrise des concepts',
    due_reviews: 'Répétitions espacées dues',
    study_plan_progress: "Plan d'étude personnalisé",
  },
};

export function t(key: string, language: string = 'en'): string {
  const langTable = TRANSLATIONS[language] || TRANSLATIONS.en;
  return langTable[key] || TRANSLATIONS.en[key] || key;
}

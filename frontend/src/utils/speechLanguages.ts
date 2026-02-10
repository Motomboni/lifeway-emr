/**
 * Speech Recognition Language Support
 * 
 * Comprehensive list of supported languages for speech-to-text,
 * with special focus on Nigerian languages.
 */

export interface SpeechLanguage {
  code: string;
  name: string;
  nativeName: string;
  region?: string;
}

export const SPEECH_LANGUAGES: SpeechLanguage[] = [
  // English Variants
  {
    code: 'en-US',
    name: 'English (United States)',
    nativeName: 'English (US)',
    region: 'International',
  },
  {
    code: 'en-GB',
    name: 'English (United Kingdom)',
    nativeName: 'English (UK)',
    region: 'International',
  },
  {
    code: 'en-NG',
    name: 'English (Nigeria)',
    nativeName: 'English (Nigeria)',
    region: 'Nigeria',
  },
  
  // Nigerian Languages
  {
    code: 'yo-NG',
    name: 'Yoruba',
    nativeName: 'Èdè Yorùbá',
    region: 'Nigeria',
  },
  {
    code: 'ig-NG',
    name: 'Igbo',
    nativeName: 'Asụsụ Igbo',
    region: 'Nigeria',
  },
  {
    code: 'ha-NG',
    name: 'Hausa',
    nativeName: 'Hausa',
    region: 'Nigeria',
  },
  {
    code: 'pcm-NG',
    name: 'Nigerian Pidgin',
    nativeName: 'Naija',
    region: 'Nigeria',
  },
  
  // Other African Languages
  {
    code: 'sw-KE',
    name: 'Swahili',
    nativeName: 'Kiswahili',
    region: 'East Africa',
  },
  {
    code: 'zu-ZA',
    name: 'Zulu',
    nativeName: 'isiZulu',
    region: 'South Africa',
  },
  {
    code: 'af-ZA',
    name: 'Afrikaans',
    nativeName: 'Afrikaans',
    region: 'South Africa',
  },
  
  // European Languages
  {
    code: 'fr-FR',
    name: 'French',
    nativeName: 'Français',
    region: 'International',
  },
  {
    code: 'es-ES',
    name: 'Spanish',
    nativeName: 'Español',
    region: 'International',
  },
  {
    code: 'de-DE',
    name: 'German',
    nativeName: 'Deutsch',
    region: 'International',
  },
  {
    code: 'pt-PT',
    name: 'Portuguese',
    nativeName: 'Português',
    region: 'International',
  },
  {
    code: 'it-IT',
    name: 'Italian',
    nativeName: 'Italiano',
    region: 'International',
  },
  
  // Asian Languages
  {
    code: 'zh-CN',
    name: 'Chinese (Simplified)',
    nativeName: '中文 (简体)',
    region: 'Asia',
  },
  {
    code: 'ja-JP',
    name: 'Japanese',
    nativeName: '日本語',
    region: 'Asia',
  },
  {
    code: 'ko-KR',
    name: 'Korean',
    nativeName: '한국어',
    region: 'Asia',
  },
  {
    code: 'hi-IN',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    region: 'Asia',
  },
  {
    code: 'ar-SA',
    name: 'Arabic',
    nativeName: 'العربية',
    region: 'Middle East',
  },
];

/**
 * Get languages grouped by region
 */
export function getLanguagesByRegion(): Record<string, SpeechLanguage[]> {
  const grouped: Record<string, SpeechLanguage[]> = {};
  
  SPEECH_LANGUAGES.forEach((lang) => {
    const region = lang.region || 'Other';
    if (!grouped[region]) {
      grouped[region] = [];
    }
    grouped[region].push(lang);
  });
  
  return grouped;
}

/**
 * Get Nigerian languages only
 */
export function getNigerianLanguages(): SpeechLanguage[] {
  return SPEECH_LANGUAGES.filter((lang) => lang.region === 'Nigeria');
}

/**
 * Get default language based on browser settings or location
 */
export function getDefaultLanguage(): string {
  // Try to detect Nigerian locale
  const browserLang = navigator.language || 'en-US';
  
  // If browser is set to Nigeria, use Nigerian English
  if (browserLang.includes('NG') || browserLang.includes('ng')) {
    return 'en-NG';
  }
  
  // Check if browser language is supported
  const supported = SPEECH_LANGUAGES.find((lang) => lang.code === browserLang);
  if (supported) {
    return browserLang;
  }
  
  // Default to US English
  return 'en-US';
}

/**
 * Get language by code
 */
export function getLanguageByCode(code: string): SpeechLanguage | undefined {
  return SPEECH_LANGUAGES.find((lang) => lang.code === code);
}

/**
 * Check if a language code is supported
 */
export function isLanguageSupported(code: string): boolean {
  return SPEECH_LANGUAGES.some((lang) => lang.code === code);
}

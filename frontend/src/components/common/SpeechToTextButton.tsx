/**
 * SpeechToTextButton Component
 * 
 * A button component that provides speech-to-text functionality.
 * Can be used with any textarea or input field.
 * 
 * Features:
 * - Visual feedback (recording indicator)
 * - Real-time transcription preview
 * - Append or replace mode
 * - Error handling
 * - Accessibility support
 */

import React, { useState, useEffect, useRef } from 'react';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { SPEECH_LANGUAGES, getNigerianLanguages, getDefaultLanguage, getLanguageByCode } from '../../utils/speechLanguages';
import styles from './SpeechToTextButton.module.css';

export interface SpeechToTextButtonProps {
  /** Current value of the text field */
  value: string | undefined;
  /** Callback when transcription is complete */
  onTranscribe: (text: string) => void;
  /** Whether to append to existing text or replace it */
  appendMode?: boolean;
  /** Language for speech recognition (default: 'en-US') */
  lang?: string;
  /** Custom className */
  className?: string;
  /** Show transcript preview while recording */
  showPreview?: boolean;
  /** Position of the button relative to the textarea */
  position?: 'top-right' | 'bottom-right' | 'inline';
}

export default function SpeechToTextButton({
  value,
  onTranscribe,
  appendMode = true,
  lang: initialLang,
  className = '',
  showPreview = true,
  position = 'top-right',
}: SpeechToTextButtonProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [dismissedError, setDismissedError] = useState(false);
  const [selectedLang, setSelectedLang] = useState(initialLang || 'en-US');
  const [showLangSelector, setShowLangSelector] = useState(false);
  
  // Set default language on mount (safe way to access navigator)
  useEffect(() => {
    if (!initialLang) {
      try {
        const defaultLang = getDefaultLanguage();
        setSelectedLang(defaultLang);
      } catch {
        // If getDefaultLanguage fails, keep 'en-US'
      }
    }
  }, [initialLang]);
  
  // Normalize value to always be a string
  const normalizedValue = value ?? '';
  // Ref so callbacks always see latest value (avoids stale closure when chunks arrive in quick succession)
  const valueRef = useRef(normalizedValue);
  valueRef.current = normalizedValue;
  // Last interim we inserted via "Insert" — skip appending same text when it arrives as final (avoids duplication)
  const lastInsertedInterimRef = useRef('');

  const {
    isListening,
    transcript,
    interimTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    clearTranscript,
  } = useSpeechRecognition({
    continuous: true,
    interimResults: true,
    lang: selectedLang,
    onResult: (newText, isFinal) => {
      if (isFinal && newText.trim()) {
        // Skip if this final text is the same as interim we already inserted (avoids duplicate)
        if (newText.trim() === lastInsertedInterimRef.current) {
          lastInsertedInterimRef.current = '';
          return;
        }
        const currentValue = valueRef.current;
        const updatedText = appendMode
          ? currentValue
              ? `${currentValue} ${newText.trim()}`
              : newText.trim()
          : newText.trim();
        onTranscribe(updatedText);
        setDismissedError(false); // Reset error dismissal on successful transcription
      }
    },
    onError: (errorMsg) => {
      setDismissedError(false); // Show error when it occurs
    },
  });

  const handleToggle = () => {
    if (isListening) {
      stopListening();
      setIsExpanded(false);
    } else {
      lastInsertedInterimRef.current = ''; // New session — clear so next final isn't treated as duplicate of old insert
      startListening();
      setIsExpanded(true);
    }
  };

  const handleInsert = () => {
    // Only insert INTERIM text that hasn't been finalized yet
    // Final text is already inserted in real-time via onResult callback
    if (interimTranscript && interimTranscript.trim()) {
      lastInsertedInterimRef.current = interimTranscript.trim();
      const currentValue = valueRef.current;
      const newText = appendMode
        ? currentValue
            ? `${currentValue} ${interimTranscript.trim()}`
            : interimTranscript.trim()
        : interimTranscript.trim();
      onTranscribe(newText);
    }
    clearTranscript();
    stopListening();
    setIsExpanded(false);
  };

  const handleClear = () => {
    clearTranscript();
    stopListening();
    setIsExpanded(false);
  };

  // Note: Debug logging removed to reduce console noise
  // The hook now properly initializes support on mount

  // Check browser support directly as fallback (in case hook hasn't initialized)
  const SpeechRecognition = typeof window !== 'undefined' 
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null;
  const actuallySupported = isSupported || !!SpeechRecognition;

  if (!actuallySupported) {
    return (
      <div className={`${styles.unsupported} ${className}`}>
        <span className={styles.unsupportedText}>
          Speech recognition not available. Please use Chrome, Edge, or Safari.
        </span>
      </div>
    );
  }

  const displayText = transcript || interimTranscript;
  const hasText = !!displayText;

  return (
    <div
      className={`${styles.container} ${styles[position]} ${className}`}
      role="group"
      aria-label="Speech to text controls"
    >
      {/* Main button */}
      <button
        type="button"
        onClick={handleToggle}
        className={`${styles.button} ${isListening ? styles.listening : ''}`}
        aria-label={isListening ? 'Stop recording' : 'Start voice recording'}
        aria-pressed={isListening}
        title={
          isListening
            ? 'Click to stop recording'
            : 'Click to start voice recording'
        }
      >
        {isListening ? (
          <>
            <svg
              className={styles.micIcon}
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 1C10.34 1 9 2.34 9 4V12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12V4C15 2.34 13.66 1 12 1Z"
                fill="currentColor"
              />
              <path
                d="M19 10V12C19 15.87 15.87 19 12 19C8.13 19 5 15.87 5 12V10H3V12C3 16.97 7.03 21 12 21C16.97 21 21 16.97 21 12V10H19Z"
                fill="currentColor"
              />
              <circle
                className={styles.pulse}
                cx="12"
                cy="12"
                r="8"
                stroke="currentColor"
                strokeWidth="2"
                fill="none"
                opacity="0.3"
              />
            </svg>
            <span className={styles.buttonText}>Stop</span>
          </>
        ) : (
          <>
            <svg
              className={styles.micIcon}
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 14C13.1 14 14 13.1 14 12V5C14 3.9 13.1 3 12 3C10.9 3 10 3.9 10 5V12C10 13.1 10.9 14 12 14Z"
                fill="currentColor"
              />
              <path
                d="M17 12C17 14.76 14.76 17 12 17C9.24 17 7 14.76 7 12H5C5 15.87 8.13 19 12 19C15.87 19 19 15.87 19 12H17Z"
                fill="currentColor"
              />
            </svg>
            <span className={styles.buttonText}>Voice</span>
          </>
        )}
      </button>

      {/* Error message */}
      {error && !dismissedError && (
        <div className={styles.error} role="alert">
          <span className={styles.errorIcon}>⚠️</span>
          <span className={styles.errorText}>{error}</span>
          <button
            type="button"
            onClick={() => setDismissedError(true)}
            className={styles.errorClose}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      )}

      {/* Expanded panel with preview and controls */}
      {isExpanded && (
        <div className={styles.panel}>
          {showPreview && hasText && (
            <div className={styles.preview}>
              <div className={styles.previewHeader}>
                <span className={styles.previewLabel}>Preview:</span>
              </div>
              <div className={styles.previewText}>
                {displayText}
                {interimTranscript && (
                  <span className={styles.interim}>{interimTranscript}</span>
                )}
              </div>
            </div>
          )}

          {/* Language Selector */}
          <div className={styles.languageSelector}>
            <button
              type="button"
              onClick={() => setShowLangSelector(!showLangSelector)}
              className={styles.langButton}
              title="Change language"
            >
              <span className={styles.langIcon}>🌐</span>
              <span className={styles.langText}>
                {getLanguageByCode(selectedLang)?.nativeName || selectedLang}
              </span>
              <span className={styles.langArrow}>{showLangSelector ? '▲' : '▼'}</span>
            </button>
            
            {showLangSelector && (
              <div className={styles.langDropdown}>
                <div className={styles.langGroup}>
                  <div className={styles.langGroupTitle}>🇳🇬 Nigerian Languages</div>
                  {getNigerianLanguages().map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => {
                        const wasListening = isListening;
                        if (wasListening) {
                          stopListening();
                        }
                        setSelectedLang(lang.code);
                        setShowLangSelector(false);
                        // Wait a bit longer for recognition to fully stop before restarting
                        if (wasListening) {
                          setTimeout(() => {
                            startListening();
                          }, 300);
                        }
                      }}
                      className={`${styles.langOption} ${selectedLang === lang.code ? styles.langOptionActive : ''}`}
                    >
                      <span className={styles.langOptionName}>{lang.nativeName}</span>
                      <span className={styles.langOptionCode}>{lang.name}</span>
                    </button>
                  ))}
                </div>
                
                <div className={styles.langGroup}>
                  <div className={styles.langGroupTitle}>Other Languages</div>
                  {SPEECH_LANGUAGES.filter((lang) => lang.region !== 'Nigeria').map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => {
                        const wasListening = isListening;
                        if (wasListening) {
                          stopListening();
                        }
                        setSelectedLang(lang.code);
                        setShowLangSelector(false);
                        // Wait a bit longer for recognition to fully stop before restarting
                        if (wasListening) {
                          setTimeout(() => {
                            startListening();
                          }, 300);
                        }
                      }}
                      className={`${styles.langOption} ${selectedLang === lang.code ? styles.langOptionActive : ''}`}
                    >
                      <span className={styles.langOptionName}>{lang.nativeName}</span>
                      <span className={styles.langOptionCode}>{lang.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {isListening && (
            <div className={styles.status}>
              <span className={styles.statusDot}></span>
              <span className={styles.statusText}>Listening in {getLanguageByCode(selectedLang)?.nativeName || selectedLang}...</span>
            </div>
          )}

          <div className={styles.actions}>
            {hasText && (
              <>
                <button
                  type="button"
                  onClick={handleInsert}
                  className={`${styles.actionButton} ${styles.insertButton}`}
                  title="Insert transcribed text"
                >
                  ✓ Insert
                </button>
                <button
                  type="button"
                  onClick={handleClear}
                  className={`${styles.actionButton} ${styles.clearButton}`}
                  title="Clear transcription"
                >
                  Clear
                </button>
              </>
            )}
            <button
              type="button"
              onClick={handleToggle}
              className={`${styles.actionButton} ${styles.stopButton}`}
              title="Stop recording"
            >
              Stop
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

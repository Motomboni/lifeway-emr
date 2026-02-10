/**
 * useSpeechRecognition Hook
 * 
 * Provides speech-to-text functionality using the Web Speech API.
 * Features:
 * - Real-time transcription
 * - Continuous recognition
 * - Error handling
 * - Browser compatibility checks
 * - Language support
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface SpeechRecognitionOptions {
  continuous?: boolean;
  interimResults?: boolean;
  lang?: string;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: string) => void;
}

export interface SpeechRecognitionState {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
}

// Type definitions for Web Speech API
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message: string;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

declare global {
  interface Window {
    SpeechRecognition: {
      new (): SpeechRecognition;
    };
    webkitSpeechRecognition: {
      new (): SpeechRecognition;
    };
  }
}

export function useSpeechRecognition(
  options: SpeechRecognitionOptions = {}
): SpeechRecognitionState {
  const {
    continuous = true,
    interimResults = true,
    lang = 'en-US',
    onResult,
    onError,
  } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  // Initialize support synchronously when window is available (avoids "Browser support: false" flash)
  const [isSupported, setIsSupported] = useState(() =>
    typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  );

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalTranscriptRef = useRef('');
  /** Length of transcript already sent to onResult (avoids duplicating when API sends same/cumulative results) */
  const sentLengthRef = useRef(0);
  /** Last delta we sent (skip sending again if API sends same final twice) */
  const lastSentDeltaRef = useRef('');
  // Use ref to track actual listening state (avoids stale closure issues)
  const isListeningRef = useRef(false);
  // Track if we're in the middle of stopping (to prevent start during stop)
  const isStoppingRef = useRef(false);
  
  // Use refs for callbacks to prevent re-initialization
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);
  
  // Update refs when callbacks change (without causing re-initialization)
  useEffect(() => {
    onResultRef.current = onResult;
    onErrorRef.current = onError;
  }, [onResult, onError]);

  // Sync support on mount (in case initial state ran in SSR or before window)
  useEffect(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const supported = !!SpeechRecognitionAPI;
    setIsSupported(supported);
    if (!supported) {
      setError('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
    }
  }, []);

  // Create/update recognition instance when settings change
  useEffect(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognitionAPI) {
      return;
    }

    // If currently listening, stop first before recreating
    if (isListeningRef.current && recognitionRef.current) {
      try {
        recognitionRef.current.abort();
        isListeningRef.current = false;
        setIsListening(false);
      } catch (err) {
        // Ignore
      }
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognition.lang = lang;

    // Reset accumulated transcript and sent length when recognition is recreated (e.g. language change)
    finalTranscriptRef.current = '';
    sentLengthRef.current = 0;
    lastSentDeltaRef.current = '';
    setTranscript('');
    setInterimTranscript('');

    // Handle results
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcriptText = result[0].transcript;

        if (result.isFinal) {
          final += transcriptText + ' ';
        } else {
          interim += transcriptText;
        }
      }

      if (final) {
        // Accumulate for internal state display
        finalTranscriptRef.current += final;
        setTranscript(finalTranscriptRef.current);
        setInterimTranscript('');
        // Send only the delta we haven't sent yet (avoids duplication when API sends same/cumulative results)
        const full = finalTranscriptRef.current;
        const delta = full.slice(sentLengthRef.current).trim();
        if (delta) {
          sentLengthRef.current = full.length;
          // Skip duplicate: same segment sent again by the API
          if (delta !== lastSentDeltaRef.current) {
            lastSentDeltaRef.current = delta;
            onResultRef.current?.(delta, true);
          }
        }
      } else if (interim) {
        setInterimTranscript(interim);
        onResultRef.current?.(interim, false);
      }
    };

    // Handle errors
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // Ignore "aborted" errors - these are expected when user stops
      if (event.error === 'aborted') {
        return;
      }

      let errorMessage = 'Speech recognition error occurred.';

      switch (event.error) {
        case 'no-speech':
          errorMessage = 'No speech detected. Please try again.';
          break;
        case 'audio-capture':
          errorMessage = 'No microphone found. Please check your microphone settings.';
          break;
        case 'not-allowed':
          errorMessage = 'Microphone permission denied. Please allow microphone access.';
          break;
        case 'network':
          errorMessage = 'Network error. Please check your internet connection.';
          break;
        default:
          errorMessage = `Speech recognition error: ${event.error}`;
      }

      setError(errorMessage);
      isListeningRef.current = false;
      setIsListening(false);
      onErrorRef.current?.(errorMessage);
    };

    // Handle end
    recognition.onend = () => {
      isListeningRef.current = false;
      isStoppingRef.current = false;
      setIsListening(false);
    };

    // Handle start — reset transcript and sent state so each recording session is fresh
    recognition.onstart = () => {
      setError(null);
      isListeningRef.current = true;
      isStoppingRef.current = false;
      setIsListening(true);
      finalTranscriptRef.current = '';
      sentLengthRef.current = 0;
      lastSentDeltaRef.current = '';
      setTranscript('');
      setInterimTranscript('');
    };

    recognitionRef.current = recognition;

    return () => {
      // Clean up on unmount or before recreating
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (err) {
          // Ignore
        }
      }
    };
  }, [continuous, interimResults, lang]);

  const startListening = useCallback(() => {
    if (!isSupported) {
      const errorMsg = 'Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.';
      setError(errorMsg);
      onErrorRef.current?.(errorMsg);
      return;
    }

    if (!recognitionRef.current) {
      const errorMsg = 'Speech recognition is not initialized. Please refresh the page.';
      setError(errorMsg);
      onErrorRef.current?.(errorMsg);
      return;
    }

    // If stopping, wait a moment
    if (isStoppingRef.current) {
      setTimeout(() => startListening(), 100);
      return;
    }

    // If already listening, ignore (don't try to stop and restart)
    if (isListeningRef.current) {
      return;
    }

    try {
      recognitionRef.current.start();
      // State will be updated by onstart handler
    } catch (err: any) {
      // Handle "already started" gracefully
      if (err?.message?.includes('already started')) {
        // Already running, that's fine
        isListeningRef.current = true;
        setIsListening(true);
        return;
      }
      
      const errorMsg = err?.message || 'Failed to start speech recognition. Please check microphone permissions.';
      setError(errorMsg);
      onErrorRef.current?.(errorMsg);
    }
  }, [isSupported]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) {
      return;
    }

    if (!isListeningRef.current) {
      return;
    }

    try {
      isStoppingRef.current = true;
      recognitionRef.current.stop();
      // State will be updated by onend handler
    } catch (err: any) {
      // If stop fails, force the state
      isListeningRef.current = false;
      isStoppingRef.current = false;
      setIsListening(false);
    }
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    finalTranscriptRef.current = '';
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    clearTranscript,
  };
}

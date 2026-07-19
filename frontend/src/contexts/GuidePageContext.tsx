/**
 * GuidePageContext — visit/page signals for JIT hint evaluation.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

export interface GuidePageState {
  visitId?: string | number;
  visitStatus?: string;
  paymentStatus?: string;
  /** Doctor has saved at least one consultation on this visit. */
  hasConsultation?: boolean;
  /** Force-show payment hint (e.g. after close visit blocked). */
  paymentBlocked?: boolean;
}

interface GuidePageContextType {
  pageState: GuidePageState;
  updatePageState: (patch: Partial<GuidePageState>) => void;
  clearPageState: () => void;
  /** Pending Ask Guide target when user searched but did not click Show me. */
  pendingAskTarget: { targetId: string; title?: string } | null;
  setPendingAskTarget: (value: { targetId: string; title?: string } | null) => void;
  /** Consultation page registers macro insertion for command palette. */
  applyMacroTrigger: (trigger: string) => boolean;
  registerMacroHandler: (handler: ((trigger: string) => boolean) | null) => void;
}

const GuidePageContext = createContext<GuidePageContextType | undefined>(undefined);

export function GuidePageProvider({ children }: { children: React.ReactNode }) {
  const [pageState, setPageState] = useState<GuidePageState>({});
  const [pendingAskTarget, setPendingAskTarget] = useState<{
    targetId: string;
    title?: string;
  } | null>(null);
  const macroHandlerRef = useRef<((trigger: string) => boolean) | null>(null);

  const registerMacroHandler = useCallback((handler: ((trigger: string) => boolean) | null) => {
    macroHandlerRef.current = handler;
  }, []);

  const applyMacroTrigger = useCallback((trigger: string) => {
    return macroHandlerRef.current?.(trigger) ?? false;
  }, []);

  const updatePageState = useCallback((patch: Partial<GuidePageState>) => {
    setPageState((prev) => ({ ...prev, ...patch }));
  }, []);

  const clearPageState = useCallback(() => {
    setPageState({});
  }, []);

  const value = useMemo(
    () => ({
      pageState,
      updatePageState,
      clearPageState,
      pendingAskTarget,
      setPendingAskTarget,
      applyMacroTrigger,
      registerMacroHandler,
    }),
    [pageState, updatePageState, clearPageState, pendingAskTarget, applyMacroTrigger, registerMacroHandler]
  );

  return <GuidePageContext.Provider value={value}>{children}</GuidePageContext.Provider>;
}

export function useGuidePage(): GuidePageContextType {
  const context = useContext(GuidePageContext);
  if (!context) {
    throw new Error('useGuidePage must be used within GuidePageProvider');
  }
  return context;
}

/** Sync page state from a component — resets registered fields on unmount. */
export function useRegisterGuidePage(patch: GuidePageState): void {
  const { updatePageState } = useGuidePage();

  useEffect(() => {
    updatePageState(patch);
    return () => {
      const reset: Partial<GuidePageState> = {};
      (Object.keys(patch) as (keyof GuidePageState)[]).forEach((key) => {
        reset[key] = undefined;
      });
      updatePageState(reset);
    };
  }, [
    updatePageState,
    patch.visitId,
    patch.visitStatus,
    patch.paymentStatus,
    patch.hasConsultation,
    patch.paymentBlocked,
  ]);
}

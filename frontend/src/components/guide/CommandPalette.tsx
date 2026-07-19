/**
 * CommandPalette — Ctrl+K / / quick actions (navigate, guide, macros, sandbox).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import { useGuidePage } from '../../contexts/GuidePageContext';
import { logGuideEvent } from '../../api/guide';
import { filterGuideCommands } from '../../utils/guideCommandSearch';
import type { GuideCommand } from '../../types/guide';
import { useGuideSandboxNavigation } from './RoleLaunchTour';
import styles from '../../styles/Guide.module.css';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

export default function CommandPalette() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { openDrawer, showSpotlightForTarget, guideModules } = useGuide();
  const { applyMacroTrigger } = useGuidePage();
  const { openSandboxPractice } = useGuideSandboxNavigation();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlightIndex, setHighlightIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(
    () => filterGuideCommands(query, user?.role, guideModules),
    [query, user?.role, guideModules]
  );

  const openPalette = useCallback(() => {
    setQuery('');
    setHighlightIndex(0);
    setOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    setOpen(false);
    setQuery('');
    setHighlightIndex(0);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((current) => !current);
        if (!open) {
          setQuery('');
          setHighlightIndex(0);
        }
        return;
      }

      if (open) return;

      if (event.key === '/' && !isEditableTarget(event.target)) {
        event.preventDefault();
        openPalette();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, openPalette]);

  useEffect(() => {
    if (!open) return undefined;
    window.setTimeout(() => inputRef.current?.focus(), 50);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closePalette();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, closePalette]);

  useEffect(() => {
    setHighlightIndex(0);
  }, [query]);

  useEffect(() => {
    if (highlightIndex >= results.length) {
      setHighlightIndex(Math.max(0, results.length - 1));
    }
  }, [highlightIndex, results.length]);

  const runCommand = useCallback(
    async (command: GuideCommand) => {
      closePalette();
      void logGuideEvent({
        event_type: 'command_palette',
        metadata: { command_id: command.id },
      }).catch(() => {});

      switch (command.action) {
        case 'navigate':
          if (command.path) navigate(command.path);
          break;
        case 'guide':
          if (command.guideTarget === 'guide-orb') {
            openDrawer();
          } else if (command.guideTarget) {
            await showSpotlightForTarget(command.guideTarget, command.label);
          }
          break;
        case 'sandbox':
          await openSandboxPractice();
          break;
        case 'macro':
          if (command.macroTrigger) {
            const applied = applyMacroTrigger(command.macroTrigger);
            if (!applied) {
              openDrawer();
            }
          }
          break;
        default:
          break;
      }
    },
    [
      applyMacroTrigger,
      closePalette,
      navigate,
      openDrawer,
      openSandboxPractice,
      showSpotlightForTarget,
    ]
  );

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setHighlightIndex((index) => Math.min(index + 1, Math.max(0, results.length - 1)));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === 'Enter' && results[highlightIndex]) {
      event.preventDefault();
      void runCommand(results[highlightIndex]);
    }
  };

  if (!open) return null;

  return createPortal(
    <>
      <div className={styles.commandBackdrop} onClick={closePalette} role="presentation" />
      <div
        className={styles.commandPalette}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <input
          ref={inputRef}
          className={styles.commandInput}
          type="search"
          placeholder="Search commands — navigate, guide, macros…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={handleInputKeyDown}
          autoComplete="off"
          spellCheck={false}
        />

        <ul className={styles.commandList} role="listbox">
          {results.length === 0 ? (
            <li className={styles.commandEmpty}>No matching commands</li>
          ) : (
            results.map((command, index) => (
              <li key={command.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={index === highlightIndex}
                  className={`${styles.commandItem} ${
                    index === highlightIndex ? styles.commandItemActive : ''
                  }`}
                  onMouseEnter={() => setHighlightIndex(index)}
                  onClick={() => void runCommand(command)}
                >
                  <span className={styles.commandLabel}>{command.label}</span>
                  <span className={styles.commandAction}>{command.action}</span>
                </button>
              </li>
            ))
          )}
        </ul>

        <div className={styles.commandFooter}>
          <span>↑↓ navigate</span>
          <span>↵ run</span>
          <span>esc close</span>
          {user?.role === 'DOCTOR' && (
            <span className={styles.commandMacroHint}>
              Macros: {CONSULTATION_MACROS.map((macro) => macro.trigger).join(' ')} + Tab
            </span>
          )}
        </div>
      </div>
    </>,
    document.body
  );
}

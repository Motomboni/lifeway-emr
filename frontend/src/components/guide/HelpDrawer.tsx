/**
 * HelpDrawer — searchable Ask Guide panel with role-filtered articles.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { askGuide, logGuideEvent } from '../../api/guide';
import { useAuth } from '../../contexts/AuthContext';
import { useGuide } from '../../contexts/GuideContext';
import { useGuidePage } from '../../contexts/GuidePageContext';
import { getRoleLaunchSteps } from '../../data/roleLaunchSteps';
import { roleSupportsSandbox } from '../../utils/roleLaunchPaths';
import type { AskGuideResponse } from '../../types/guide';
import { useGuideSandboxNavigation } from './RoleLaunchTour';
import styles from '../../styles/Guide.module.css';

export default function HelpDrawer() {
  const { user } = useAuth();
  const {
    drawerOpen,
    closeDrawer,
    showSpotlightForTarget,
    isRoleLaunchComplete,
    resumeRoleLaunch,
    startRoleLaunch,
    sandboxLoading,
    getRoleLaunchResumeIndex,
    guideModules,
  } = useGuide();
  const { openSandboxPractice } = useGuideSandboxNavigation();
  const { setPendingAskTarget } = useGuidePage();
  const [query, setQuery] = useState('');
  const [asking, setAsking] = useState(false);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [response, setResponse] = useState<AskGuideResponse | null>(null);
  const [articles, setArticles] = useState<AskGuideResponse['articles']>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const launchSteps = getRoleLaunchSteps(user?.role, guideModules);
  const canSandbox = roleSupportsSandbox(user?.role);
  const resumeIndex = getRoleLaunchResumeIndex();
  const hasPartialProgress = resumeIndex > 0;

  const loadRoleArticles = useCallback(async () => {
    setLoadingArticles(true);
    try {
      const result = await askGuide(' ');
      setArticles(result.articles);
    } catch {
      setArticles([]);
    } finally {
      setLoadingArticles(false);
    }
  }, []);

  useEffect(() => {
    if (!drawerOpen) return;
    setQuery('');
    setResponse(null);
    setError(null);
    loadRoleArticles();
    window.setTimeout(() => inputRef.current?.focus(), 100);
  }, [drawerOpen, loadRoleArticles]);

  useEffect(() => {
    if (!drawerOpen) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeDrawer();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen, closeDrawer]);

  const handleAsk = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setAsking(true);
    setError(null);
    try {
      const result = await askGuide(trimmed);
      setResponse(result);
      if (result.guide_target) {
        setPendingAskTarget({
          targetId: result.guide_target,
          title: result.articles[0]?.title,
        });
      } else {
        setPendingAskTarget(null);
      }
      if (result.articles.length > 0) {
        setArticles(result.articles);
      }
    } catch {
      setError('Could not reach the guide. Check your connection and try again.');
    } finally {
      setAsking(false);
    }
  };

  const handleShowMe = async (targetId: string | null, title?: string) => {
    if (!targetId) return;
    setPendingAskTarget(null);
    closeDrawer();
    await showSpotlightForTarget(targetId, title);
  };

  const handleArticleClick = async (article: AskGuideResponse['articles'][0]) => {
    void logGuideEvent({
      event_type: 'article_open',
      article_id: article.id,
      target_id: article.guide_target ?? undefined,
    }).catch(() => {});
    setResponse({
      query: article.title,
      answer: article.summary,
      articles: [article],
      guide_target: article.guide_target,
    });
    if (article.guide_target) {
      await handleShowMe(article.guide_target, article.title);
    }
  };

  if (!drawerOpen) return null;

  return createPortal(
    <>
      <div
        className={styles.drawerBackdrop}
        onClick={closeDrawer}
        role="presentation"
        aria-hidden="true"
      />
      <aside
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-drawer-title"
      >
        <div className={styles.drawerHeader}>
          <h2 id="guide-drawer-title">Guide</h2>
          <button
            type="button"
            className={styles.drawerClose}
            onClick={closeDrawer}
            aria-label="Close guide"
          >
            ×
          </button>
        </div>

        <div className={styles.drawerBody}>
          {!isRoleLaunchComplete && launchSteps.length > 0 && (
            <>
              <p className={styles.sectionLabel}>Getting started</p>
              <div className={styles.gettingStartedCard}>
                <p>
                  {hasPartialProgress
                    ? `Resume your tour — step ${resumeIndex + 1} of ${launchSteps.length}.`
                    : `New here? Take a quick ${launchSteps.length}-step tour for ${user?.role?.toLowerCase().replace('_', ' ')}s.`}
                </p>
                <div className={styles.gettingStartedActions}>
                  <button
                    type="button"
                    className={styles.launchPrimary}
                    onClick={hasPartialProgress ? resumeRoleLaunch : startRoleLaunch}
                  >
                    {hasPartialProgress ? 'Resume tour' : 'Start tour'}
                  </button>
                  {canSandbox && (
                    <button
                      type="button"
                      className={styles.launchSecondary}
                      onClick={() => void openSandboxPractice()}
                      disabled={sandboxLoading}
                    >
                      {sandboxLoading ? 'Opening…' : 'Practice in sandbox'}
                    </button>
                  )}
                </div>
              </div>
            </>
          )}

          {isRoleLaunchComplete && canSandbox && (
            <>
              <p className={styles.sectionLabel}>Practice</p>
              <div className={styles.gettingStartedCard}>
                <p>Try features safely on a demo patient — no real PHI.</p>
                <button
                  type="button"
                  className={styles.launchSecondary}
                  onClick={() => void openSandboxPractice()}
                  disabled={sandboxLoading}
                >
                  {sandboxLoading ? 'Opening…' : 'Open sandbox visit'}
                </button>
              </div>
            </>
          )}

          <form className={styles.askSection} onSubmit={handleAsk}>
            <label htmlFor="guide-ask-input">Ask Guide</label>
            <p className={styles.commandTip}>Tip: press Ctrl+K anywhere for quick commands.</p>
            <div className={styles.askRow}>
              <input
                id="guide-ask-input"
                ref={inputRef}
                className={styles.askInput}
                type="search"
                placeholder='e.g. "How do I order a lab?"'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoComplete="off"
              />
              <button type="submit" className={styles.askButton} disabled={asking || !query.trim()}>
                {asking ? '…' : 'Ask'}
              </button>
            </div>
          </form>

          {error && <p className={styles.errorText}>{error}</p>}

          {response && (
            <div className={styles.answerCard}>
              <p>{response.answer}</p>
              {response.guide_target && (
                <button
                  type="button"
                  className={styles.showMeButton}
                  onClick={() => handleShowMe(response.guide_target, response.articles[0]?.title)}
                >
                  Show me on screen
                </button>
              )}
            </div>
          )}

          <p className={styles.sectionLabel}>For your role</p>
          {loadingArticles ? (
            <p className={styles.loadingText}>Loading topics…</p>
          ) : articles.length === 0 ? (
            <p className={styles.loadingText}>No guide topics available for your role.</p>
          ) : (
            <ul className={styles.articleList}>
              {articles.map((article) => (
                <li key={article.id}>
                  <button
                    type="button"
                    className={styles.articleButton}
                    onClick={() => handleArticleClick(article)}
                  >
                    <span className={styles.articleTitle}>{article.title}</span>
                    <span className={styles.articleSummary}>{article.summary}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>,
    document.body
  );
}

/**
 * SpotlightCoach — non-blocking overlay that highlights a live UI target.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useGuide } from '../../contexts/GuideContext';
import { getGuideTargetRect } from '../../utils/guideDom';
import styles from '../../styles/Guide.module.css';

interface CardPosition {
  top: number;
  left: number;
}

function computeCardPosition(
  rect: { top: number; left: number; width: number; height: number },
  cardHeightEstimate = 160
): CardPosition {
  const margin = 12;
  const viewportH = window.innerHeight;
  const viewportW = window.innerWidth;
  const below = rect.top + rect.height + margin;
  const above = rect.top - cardHeightEstimate - margin;

  let top = below + cardHeightEstimate < viewportH ? below : Math.max(margin, above);
  let left = Math.min(
    Math.max(margin, rect.left),
    viewportW - 360 - margin
  );

  if (top < margin) top = margin;
  return { top, left };
}

export default function SpotlightCoach() {
  const { spotlight, clearSpotlight, skipRoleLaunch } = useGuide();
  const [ring, setRing] = useState<{
    top: number;
    left: number;
    width: number;
    height: number;
  } | null>(null);
  const [cardPos, setCardPos] = useState<CardPosition | null>(null);
  const [missing, setMissing] = useState(false);

  const updatePosition = useCallback(() => {
    if (!spotlight) return;
    const rect = getGuideTargetRect(spotlight.targetId);
    if (!rect) {
      setRing(null);
      setMissing(true);
      setCardPos({ top: window.innerHeight / 2 - 80, left: window.innerWidth / 2 - 160 });
      return;
    }
    setMissing(false);
    const pad = 6;
    setRing({
      top: rect.top - pad,
      left: rect.left - pad,
      width: rect.width + pad * 2,
      height: rect.height + pad * 2,
    });
    setCardPos(computeCardPosition(rect));
  }, [spotlight]);

  useEffect(() => {
    if (!spotlight) {
      setRing(null);
      setCardPos(null);
      setMissing(false);
      return undefined;
    }

    updatePosition();
    const timer = window.setTimeout(updatePosition, 200);

    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') clearSpotlight();
    };
    window.addEventListener('keydown', onKeyDown);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [spotlight, updatePosition, clearSpotlight]);

  if (!spotlight) return null;

  const handleSkip = () => {
    if (spotlight.isRoleLaunch) {
      void skipRoleLaunch();
    } else {
      clearSpotlight();
    }
  };

  const handleNext = () => {
    if (spotlight.onNext) {
      spotlight.onNext();
    } else {
      clearSpotlight();
    }
  };

  const handleComplete = () => {
    if (spotlight.onComplete) {
      spotlight.onComplete();
    } else {
      clearSpotlight();
    }
  };

  return createPortal(
    <div className={styles.spotlightLayer} role="presentation" aria-hidden={false}>
      {ring && (
        <div
          className={styles.spotlightRing}
          style={{
            top: ring.top,
            left: ring.left,
            width: ring.width,
            height: ring.height,
          }}
        />
      )}
      {!ring && !missing && <div className={styles.spotlightOverlay} />}

      {cardPos && (
        <div
          className={styles.spotlightCard}
          style={{ top: cardPos.top, left: cardPos.left }}
          role="dialog"
          aria-labelledby="guide-spotlight-title"
          aria-describedby="guide-spotlight-body"
        >
          {spotlight.stepIndex != null && spotlight.stepTotal != null && (
            <div className={styles.spotlightStep}>
              Step {spotlight.stepIndex + 1} of {spotlight.stepTotal}
            </div>
          )}
          <h3 id="guide-spotlight-title">{spotlight.title}</h3>
          <p id="guide-spotlight-body">
            {missing
              ? 'This item is not visible on the current screen. Navigate to the relevant page or expand the section, then try again.'
              : spotlight.body}
          </p>
          <div className={styles.spotlightActions}>
            <button type="button" className={styles.spotlightSkip} onClick={handleSkip}>
              {missing ? 'Close' : spotlight.isRoleLaunch ? 'Skip tour' : 'Skip'}
            </button>
            {spotlight.onNext && !missing && (
              <button type="button" className={styles.spotlightNext} onClick={handleNext}>
                Next
              </button>
            )}
            {spotlight.onComplete && !missing && (
              <button type="button" className={styles.spotlightNext} onClick={handleComplete}>
                Done
              </button>
            )}
            {!spotlight.onNext && !spotlight.onComplete && !missing && (
              <button type="button" className={styles.spotlightNext} onClick={clearSpotlight}>
                Got it
              </button>
            )}
          </div>
        </div>
      )}
    </div>,
    document.body
  );
}

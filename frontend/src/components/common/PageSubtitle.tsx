/**
 * Page header subtitle — readable on the gradient canvas in light and dark theme.
 * Dark theme still uses a pale top gradient, so subtitles need a text-shadow like h1.
 */
import React, { useLayoutEffect, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

const SUBTITLE_STYLE = {
  light: {
    color: '#0f172a',
    textShadow: '0 1px 2px rgba(255, 255, 255, 0.95), 0 0 20px rgba(255, 255, 255, 0.65)',
  },
  dark: {
    color: '#f8fafc',
    textShadow: '0 1px 4px rgba(0, 0, 0, 0.8), 0 0 1px rgba(0, 0, 0, 0.9)',
  },
} as const;

interface PageSubtitleProps {
  children: React.ReactNode;
  className?: string;
}

export default function PageSubtitle({ children, className = '' }: PageSubtitleProps) {
  const { theme } = useTheme();
  const ref = useRef<HTMLParagraphElement>(null);
  const palette = SUBTITLE_STYLE[theme];

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty('color', palette.color, 'important');
    el.style.setProperty('-webkit-text-fill-color', palette.color, 'important');
    el.style.setProperty('text-shadow', palette.textShadow, 'important');
    el.style.setProperty('opacity', '1', 'important');
    el.style.setProperty('visibility', 'visible', 'important');
  }, [palette.color, palette.textShadow]);

  return (
    <p
      ref={ref}
      className={className ? `emr-page-desc ${className}` : 'emr-page-desc'}
      data-page-subtitle
      style={{
        display: 'block',
        margin: '0.5rem 0 0',
        fontSize: '1.05rem',
        fontWeight: 600,
        lineHeight: 1.55,
        maxWidth: '42rem',
      }}
    >
      {children}
    </p>
  );
}

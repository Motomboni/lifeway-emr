/**
 * Textarea with integrated speech-to-text (voice dictation).
 */
import React from 'react';
import SpeechToTextButton from './SpeechToTextButton';

interface VoiceTextareaFieldProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange'> {
  value: string;
  onValueChange: (value: string) => void;
  appendMode?: boolean;
}

export default function VoiceTextareaField({
  value,
  onValueChange,
  appendMode = true,
  className,
  ...rest
}: VoiceTextareaFieldProps) {
  return (
    <div style={{ position: 'relative', paddingTop: '2rem' }}>
      <textarea
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        className={className}
        {...rest}
      />
      <SpeechToTextButton
        value={value}
        onTranscribe={onValueChange}
        appendMode={appendMode}
        position="top-right"
        showPreview={true}
      />
    </div>
  );
}

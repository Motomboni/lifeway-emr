/**
 * MacroAwareTextarea — expands .dm2-style macros on Tab.
 */
import React from 'react';
import { ConsultationData } from '../../types/consultation';
import { buildMacroExpansion, MacroField } from '../../utils/consultationMacroExpand';

interface MacroAwareTextareaProps {
  id: string;
  field: MacroField;
  value: string;
  formData: Pick<ConsultationData, MacroField>;
  onChange: (value: string) => void;
  onMacroExpand: (updates: Partial<ConsultationData>) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
}

export default function MacroAwareTextarea({
  id,
  field,
  value,
  formData,
  onChange,
  onMacroExpand,
  placeholder,
  rows = 6,
  className,
}: MacroAwareTextareaProps) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Tab' || event.shiftKey) return;

    const updates = buildMacroExpansion(field, event.currentTarget.value, formData);
    if (!updates) return;

    event.preventDefault();
    onMacroExpand(updates);
  };

  return (
    <textarea
      id={id}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      rows={rows}
      className={className}
    />
  );
}

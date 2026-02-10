/**
 * DrugSearchInput Component
 * 
 * Autocomplete/search input for selecting drugs from the catalog.
 * Used in prescription creation to search and select drugs.
 */
import React, { useState, useEffect, useRef } from 'react';
import { fetchDrugs, Drug } from '../../api/drug';
import styles from '../../styles/DrugSearchInput.module.css';

interface DrugSearchInputProps {
  value: string;
  onChange: (drugName: string, drugCode?: string) => void;
  onDrugSelect?: (drug: Drug) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

export default function DrugSearchInput({
  value,
  onChange,
  onDrugSelect,
  placeholder = 'Search for a drug...',
  required = false,
  disabled = false,
}: DrugSearchInputProps) {
  const [searchQuery, setSearchQuery] = useState(value);
  const [suggestions, setSuggestions] = useState<Drug[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [allDrugs, setAllDrugs] = useState<Drug[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Load all drugs on mount
  useEffect(() => {
    const loadDrugs = async () => {
      try {
        setLoading(true);
        const response = await fetchDrugs();
        const drugsArray = Array.isArray(response) 
          ? response 
          : (response as any)?.results || [];
        // Only show active drugs
        const activeDrugs = drugsArray.filter((drug: Drug) => drug.is_active);
        setAllDrugs(activeDrugs);
      } catch (error) {
        console.error('Error loading drugs:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDrugs();
  }, []);

  // Filter drugs based on search query
  useEffect(() => {
    if (searchQuery.trim().length === 0) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const query = searchQuery.toLowerCase().trim();
    const filtered = allDrugs.filter((drug) => {
      const nameMatch = drug.name.toLowerCase().includes(query);
      const genericMatch = drug.generic_name?.toLowerCase().includes(query);
      const codeMatch = drug.drug_code?.toLowerCase().includes(query);
      return nameMatch || genericMatch || codeMatch;
    });

    setSuggestions(filtered.slice(0, 10)); // Limit to 10 suggestions
    setShowSuggestions(filtered.length > 0);
    setSelectedIndex(-1);
  }, [searchQuery, allDrugs]);

  // Sync searchQuery with value prop
  useEffect(() => {
    setSearchQuery(value);
  }, [value]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setSearchQuery(newValue);
    onChange(newValue);
    setShowSuggestions(true);
  };

  const handleDrugSelect = (drug: Drug) => {
    setSearchQuery(drug.name);
    onChange(drug.name, drug.drug_code || undefined);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    
    if (onDrugSelect) {
      onDrugSelect(drug);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleDrugSelect(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleBlur = () => {
    // Delay hiding suggestions to allow click events
    setTimeout(() => {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }, 200);
  };

  const handleFocus = () => {
    if (searchQuery.trim().length > 0 && suggestions.length > 0) {
      setShowSuggestions(true);
    }
  };

  return (
    <div className={styles.drugSearchContainer}>
      <input
        ref={inputRef}
        type="text"
        value={searchQuery}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        onFocus={handleFocus}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={styles.drugSearchInput}
        autoComplete="off"
      />
      {loading && (
        <div className={styles.loadingIndicator}>Loading drugs...</div>
      )}
      {showSuggestions && suggestions.length > 0 && (
        <div ref={suggestionsRef} className={styles.suggestionsList}>
          {suggestions.map((drug, index) => (
            <div
              key={drug.id}
              className={`${styles.suggestionItem} ${
                index === selectedIndex ? styles.selected : ''
              }`}
              onClick={() => handleDrugSelect(drug)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className={styles.suggestionName}>{drug.name}</div>
              {drug.generic_name && (
                <div className={styles.suggestionGeneric}>
                  Generic: {drug.generic_name}
                </div>
              )}
              {drug.drug_code && (
                <div className={styles.suggestionCode}>Code: {drug.drug_code}</div>
              )}
              {drug.dosage_forms && (
                <div className={styles.suggestionDetails}>
                  Forms: {drug.dosage_forms}
                </div>
              )}
              {drug.common_dosages && (
                <div className={styles.suggestionDetails}>
                  Dosages: {drug.common_dosages}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {showSuggestions && searchQuery.trim().length > 0 && suggestions.length === 0 && !loading && (
        <div className={styles.noResults}>No drugs found matching "{searchQuery}"</div>
      )}
    </div>
  );
}


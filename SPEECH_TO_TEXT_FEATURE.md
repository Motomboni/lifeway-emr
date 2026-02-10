# Speech-to-Text Feature Documentation

## Overview

The EMR system now includes a world-class speech-to-text feature that allows doctors and healthcare providers to dictate consultation notes, examination findings, diagnoses, and clinical notes using their voice. This significantly improves workflow efficiency and reduces documentation time.

## Features

### ✨ Key Capabilities

- **Real-time Transcription**: See your words appear as you speak
- **Continuous Recognition**: Keep talking without interruption
- **Visual Feedback**: Clear indicators when recording is active
- **Preview Panel**: Review transcribed text before inserting
- **Append Mode**: Add to existing text or replace it
- **Error Handling**: Graceful handling of microphone permissions and errors
- **Browser Support**: Works with Chrome, Edge, and Safari (Web Speech API)

### 🎯 Where It's Available

The speech-to-text button is integrated into all consultation form sections:

1. **History Section** - Patient history, chief complaint, and presenting symptoms
2. **Examination Section** - Physical examination findings and clinical observations
3. **Diagnosis Section** - Clinical diagnosis, differential diagnosis, and assessment
4. **Clinical Notes Section** - Additional clinical notes, treatment plan, and follow-up instructions

## How to Use

### Basic Usage

1. **Start Recording**: Click the "Voice" button in the top-right corner of any textarea
2. **Speak Clearly**: The system will transcribe your speech in real-time
3. **Review Preview**: Check the preview panel to see what was transcribed
4. **Insert Text**: Click "Insert" to add the transcribed text to the field
5. **Stop Recording**: Click "Stop" when finished

### Advanced Features

#### Append vs Replace Mode

- **Append Mode (Default)**: New transcription is added to existing text with a space
- **Replace Mode**: New transcription replaces all existing text

#### Continuous Recognition

The system continues listening until you click "Stop", allowing for natural conversation flow.

#### Error Handling

If microphone permission is denied or an error occurs:
- A clear error message is displayed
- The error can be dismissed
- The system gracefully handles network issues

## Technical Details

### Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | ✅ Full | Best experience |
| Edge | ✅ Full | Chromium-based |
| Safari | ✅ Full | macOS/iOS |
| Firefox | ❌ Not Supported | Web Speech API not available |

### Language Support

The default language is `en-US` (English - United States). The system can be configured to support other languages by changing the `lang` prop.

### Privacy & Security

- **No Cloud Processing**: Uses browser's built-in Web Speech API (client-side)
- **No Data Transmission**: Audio never leaves your device
- **Local Processing**: All transcription happens in your browser
- **No Storage**: Audio is not recorded or stored

### Performance

- **Low Latency**: Real-time transcription with minimal delay
- **Lightweight**: No additional dependencies or API keys required
- **Efficient**: Uses native browser capabilities

## Component Architecture

### Files Created

1. **`useSpeechRecognition.ts`** - Custom React hook for speech recognition
2. **`SpeechToTextButton.tsx`** - Reusable button component
3. **`SpeechToTextButton.module.css`** - Styling for the component

### Integration Points

The feature is integrated into:
- `HistorySection.tsx`
- `ExaminationSection.tsx`
- `DiagnosisSection.tsx`
- `ClinicalNotesSection.tsx`

## Customization

### Changing Language

To change the recognition language, modify the `lang` prop:

```tsx
<SpeechToTextButton
  lang="en-GB"  // British English
  // or
  lang="es-ES"  // Spanish
  // etc.
/>
```

### Positioning

The button can be positioned in three ways:
- `top-right` (default) - Top right corner of textarea
- `bottom-right` - Bottom right corner
- `inline` - Inline with other elements

### Disabling Preview

To hide the preview panel:

```tsx
<SpeechToTextButton
  showPreview={false}
/>
```

## Troubleshooting

### Microphone Not Working

1. **Check Permissions**: Ensure your browser has microphone access
2. **Browser Settings**: Go to browser settings and allow microphone for this site
3. **System Settings**: Check your operating system's microphone permissions

### No Speech Detected

1. **Check Microphone**: Ensure your microphone is connected and working
2. **Speak Clearly**: Speak clearly and at a normal volume
3. **Reduce Background Noise**: Minimize background noise for better accuracy

### Transcription Not Accurate

1. **Speak Clearly**: Enunciate words clearly
2. **Reduce Noise**: Work in a quiet environment
3. **Check Language**: Ensure the correct language is selected
4. **Browser**: Use Chrome or Edge for best accuracy

### Button Not Appearing

1. **Browser Support**: Ensure you're using a supported browser (Chrome, Edge, Safari)
2. **Check Console**: Look for any JavaScript errors in the browser console
3. **Refresh Page**: Try refreshing the page

## Future Enhancements

Potential improvements for future versions:

- [ ] Support for multiple languages in the same session
- [ ] Custom vocabulary for medical terms
- [ ] Offline transcription support
- [ ] Integration with cloud-based services for better accuracy
- [ ] Voice commands for navigation
- [ ] Automatic punctuation and formatting
- [ ] Medical terminology auto-correction

## Support

For issues or questions:
1. Check browser compatibility
2. Verify microphone permissions
3. Review browser console for errors
4. Contact system administrator

---

**Note**: This feature uses the Web Speech API, which requires an internet connection for initial setup but processes audio locally in your browser.

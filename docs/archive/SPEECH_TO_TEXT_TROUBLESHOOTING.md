# Speech-to-Text Troubleshooting Guide

## Quick Checks

### 1. Browser Compatibility
- ✅ **Chrome** - Full support (recommended)
- ✅ **Edge** - Full support
- ✅ **Safari** - Full support
- ❌ **Firefox** - Not supported

**Action:** Make sure you're using Chrome, Edge, or Safari.

### 2. Microphone Permissions

**Check permissions:**
1. Click the "Voice" button
2. Browser should prompt for microphone access
3. Click "Allow" when prompted

**If permission was denied:**
- **Chrome/Edge:** Click the lock icon in the address bar → Site settings → Microphone → Allow
- **Safari:** Safari → Preferences → Websites → Microphone → Allow for this site

### 3. Check Browser Console

Open Developer Tools (F12) and check the Console tab for messages:

**Expected messages when working:**
```
[useSpeechRecognition] Browser support check: {supported: true, ...}
[useSpeechRecognition] Initialized with language: en-US
[Speech Recognition] Started listening in language: en-US
```

**Error messages to look for:**
- `Speech recognition is not supported` → Wrong browser
- `Microphone permission denied` → Need to allow microphone access
- `No microphone found` → Check hardware
- `Network error` → Internet connection required (for Chrome/Edge)

### 4. Test Steps

1. **Open a consultation form** (or any form with speech-to-text)
2. **Click the "Voice" button** in the top-right of a textarea
3. **Check the console** (F12) for any error messages
4. **Look for the error message** in the UI (red warning box)
5. **Try speaking** - you should see text appear in the preview panel

## Common Issues and Solutions

### Issue: Button doesn't respond when clicked

**Possible causes:**
- Browser not supported
- JavaScript error preventing click handler

**Solution:**
1. Check browser console for errors (F12)
2. Verify you're using Chrome, Edge, or Safari
3. Try refreshing the page

### Issue: "Microphone permission denied"

**Solution:**
1. Click the lock icon (🔒) in the browser address bar
2. Find "Microphone" in site settings
3. Change from "Block" to "Allow"
4. Refresh the page
5. Try clicking the Voice button again

### Issue: "No speech detected"

**Possible causes:**
- Microphone not working
- Speaking too quietly
- Background noise too loud

**Solution:**
1. Test microphone in another app (e.g., voice recorder)
2. Speak clearly and at normal volume
3. Reduce background noise
4. Check microphone is not muted in system settings

### Issue: Button shows "Speech recognition not available"

**This means:**
- Browser doesn't support Web Speech API (likely Firefox)

**Solution:**
- Switch to Chrome, Edge, or Safari

### Issue: Text appears in preview but doesn't insert

**Solution:**
1. Make sure you click the "✓ Insert" button
2. Or wait for the final transcript (it auto-inserts when final)
3. Check that the textarea is not disabled

### Issue: Language not working

**Solution:**
1. Click the globe icon (🌐) to change language
2. Make sure the language is supported by your browser
3. Some Nigerian languages may have limited support
4. Try English first to verify the feature works

## Debug Mode

The code now includes console logging. To see detailed debug info:

1. Open Developer Tools (F12)
2. Go to Console tab
3. Click the Voice button
4. Look for messages starting with `[useSpeechRecognition]` or `[SpeechToTextButton]`

## Testing Checklist

- [ ] Using Chrome, Edge, or Safari
- [ ] Microphone permissions granted
- [ ] Internet connection active (for Chrome/Edge)
- [ ] Microphone hardware working
- [ ] No console errors
- [ ] Button appears in textarea
- [ ] Button changes to "Stop" when clicked
- [ ] Preview panel appears
- [ ] Text appears when speaking
- [ ] "Insert" button works

## Still Not Working?

If none of the above solutions work:

1. **Check the browser console** for specific error messages
2. **Try a different browser** (Chrome is most reliable)
3. **Test microphone** in another application
4. **Check system microphone settings** (Windows Settings → Privacy → Microphone)
5. **Restart the browser** completely
6. **Clear browser cache** and reload

## Contact Support

If the issue persists, provide:
- Browser name and version
- Operating system
- Console error messages (screenshot)
- Steps to reproduce the issue

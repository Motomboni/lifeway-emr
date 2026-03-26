/**
 * Main entry point for React application
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/theme.css';
import './index.css';

// Fix "Illegal invocation" when Twilio Video SDK calls enumerateDevices() from async callbacks.
// The method must be invoked with mediaDevices as `this`; binding once avoids the error.
if (typeof navigator !== 'undefined' && navigator.mediaDevices && typeof navigator.mediaDevices.enumerateDevices === 'function') {
  navigator.mediaDevices.enumerateDevices = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
}

async function initializeServiceWorker(): Promise<void> {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  const publicUrl = process.env.PUBLIC_URL || '';
  const swUrl = `${publicUrl}/sw.js`;

  try {
    const registrations = await navigator.serviceWorker.getRegistrations();

    if (process.env.NODE_ENV === 'production') {
      // Keep only EMR workers; remove unknown workers that may hijack API requests.
      const allowedScriptSuffixes = [`${publicUrl}/sw.js`, `${publicUrl}/sw-passthrough.js`];
      let removedUnknownWorker = false;
      await Promise.all(
        registrations.map(async (registration) => {
          const scriptUrl = registration.active?.scriptURL ||
                            registration.waiting?.scriptURL ||
                            registration.installing?.scriptURL ||
                            '';
          const isAllowed = allowedScriptSuffixes.some((suffix) => scriptUrl.endsWith(suffix));
          if (!isAllowed) {
            await registration.unregister();
            removedUnknownWorker = true;
          }
        })
      );

      // If we removed a rogue SW, force one clean reload so current page is no longer controlled.
      // Guarded to avoid reload loops.
      if (removedUnknownWorker) {
        const reloadFlag = 'emr_sw_cleanup_reload_done';
        if (!sessionStorage.getItem(reloadFlag)) {
          sessionStorage.setItem(reloadFlag, '1');
          window.location.reload();
          return;
        }
      }

      const reg = await navigator.serviceWorker.register(swUrl, { scope: '/' });
      void reg.update();
      return;
    }

    // Development: always unregister all service workers before app boot.
    const hadRegistrations = registrations.length > 0;
    await Promise.all(
      registrations.map((registration) => registration.unregister())
    );

    // In dev, force one reload after cleanup so stale controller is dropped immediately.
    if (hadRegistrations) {
      const reloadFlag = 'emr_sw_cleanup_reload_done_dev';
      if (!sessionStorage.getItem(reloadFlag)) {
        sessionStorage.setItem(reloadFlag, '1');
        window.location.reload();
        return;
      }
    }
  } catch {
    // Ignore SW initialization errors to avoid blocking app boot.
  }
}

initializeServiceWorker().finally(() => {
  const root = ReactDOM.createRoot(
    document.getElementById('root') as HTMLElement
  );

  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});

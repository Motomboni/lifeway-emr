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

// Register PWA service worker: caches app shell for offline, API stays network-only.
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${process.env.PUBLIC_URL || ''}/sw.js`, { scope: '/' })
      .then((reg) => {
        reg.update();
      })
      .catch(() => {});
  });
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

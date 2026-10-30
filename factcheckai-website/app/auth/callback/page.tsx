'use client';

import { useEffect, useState } from 'react';

/**
 * Google OAuth callback page for the TruvantaAI Chrome extension.
 *
 * Flow:
 *   1. Extension opens Google OAuth with redirect_uri = this page
 *   2. Google redirects here with ?access_token=... or #access_token=...
 *   3. This page reads the token and closes itself — Chrome's launchWebAuthFlow
 *      intercepts the navigation and returns the full URL back to the extension
 *
 * This page is never seen by the user. It flashes briefly then closes.
 * No token is stored here — it's only passed back through the URL to the extension.
 */
export default function AuthCallbackPage() {
  const [status, setStatus] = useState<'processing' | 'done' | 'error'>('processing');

  useEffect(() => {
    try {
      // Token can be in the hash fragment (#access_token=...) or query string
      const hash   = window.location.hash.slice(1);
      const search = window.location.search.slice(1);
      const params = new URLSearchParams(hash || search);

      const accessToken = params.get('access_token');
      const error       = params.get('error');

      if (error) {
        setStatus('error');
        return;
      }

      if (accessToken) {
        // Chrome's launchWebAuthFlow is watching for the redirect to this URL.
        // It captures the full URL (including the token in the fragment) and
        // returns it to the extension — nothing else needs to happen here.
        setStatus('done');
      } else {
        setStatus('error');
      }
    } catch {
      setStatus('error');
    }
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: '#0a0a0b',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        color: '#ededef',
      }}
    >
      <div style={{ textAlign: 'center', padding: '32px' }}>
        {status === 'processing' && (
          <>
            <div
              style={{
                width: 40,
                height: 40,
                border: '3px solid rgba(255,197,61,0.2)',
                borderTopColor: '#ffc53d',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                margin: '0 auto 16px',
              }}
            />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <p style={{ margin: 0, fontSize: 14, color: '#a1a1aa' }}>Signing you in…</p>
          </>
        )}
        {status === 'done' && (
          <>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✓</div>
            <p style={{ margin: 0, fontSize: 14, color: '#a1a1aa' }}>
              Signed in. You can close this tab.
            </p>
          </>
        )}
        {status === 'error' && (
          <>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✕</div>
            <p style={{ margin: 0, fontSize: 14, color: '#a1a1aa' }}>
              Sign-in failed. Please try again.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

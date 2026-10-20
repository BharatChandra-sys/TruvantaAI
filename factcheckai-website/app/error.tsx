'use client';

import { useEffect } from 'react';
import MaterialSymbols from '@/components/MaterialSymbols';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to monitoring service (e.g., Sentry, LogRocket)
    console.error('Application error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <MaterialSymbols />
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <span className="material-symbols-outlined text-6xl text-error">
            error
          </span>
        </div>
        
        <h1 className="text-3xl font-bold text-on-surface mb-4">
          Something went wrong
        </h1>
        
        <p className="text-base text-on-surface-variant mb-8">
          We apologize for the inconvenience. Our team has been notified and is working on a fix.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center gap-2 bg-primary-container hover:bg-surface-tint text-on-primary-fixed font-semibold px-6 py-3 rounded transition-colors"
          >
            <span className="material-symbols-outlined">refresh</span>
            Try again
          </button>
          
          <a
            href="/"
            className="inline-flex items-center justify-center gap-2 bg-surface-container hover:bg-surface-container-high text-on-surface font-medium px-6 py-3 rounded transition-colors"
          >
            <span className="material-symbols-outlined">home</span>
            Go home
          </a>
        </div>
        
        {error.digest && (
          <p className="mt-8 text-xs text-on-surface-variant font-mono">
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  );
}

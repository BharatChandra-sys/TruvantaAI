import Link from 'next/link';
import MaterialSymbols from '@/components/MaterialSymbols';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <MaterialSymbols />
      <Header />
      
      <main className="flex-1 flex items-center justify-center px-4 pt-24">
        <div className="max-w-md w-full text-center">
          <div className="mb-8">
            <span className="material-symbols-outlined text-8xl text-surface-tint">
              search_off
            </span>
          </div>
          
          <h1 className="text-6xl font-bold text-on-surface mb-4">404</h1>
          
          <h2 className="text-2xl font-semibold text-on-surface mb-4">
            Page not found
          </h2>
          
          <p className="text-base text-on-surface-variant mb-8">
            The page you're looking for doesn't exist or has been moved.
          </p>
          
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-primary-container hover:bg-surface-tint text-on-primary-fixed font-semibold px-6 py-3 rounded transition-colors"
          >
            <span className="material-symbols-outlined">home</span>
            Back to home
          </Link>
        </div>
      </main>
      
      <Footer />
    </div>
  );
}

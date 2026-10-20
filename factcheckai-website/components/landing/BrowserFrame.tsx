export default function BrowserFrame({
  url,
  children,
  className = '',
}: {
  url: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`elevated overflow-hidden rounded-[24px] bg-raised ${className}`}>
      <div className="flex h-10 items-center justify-center border-b border-line bg-panel px-4">
        <div className="flex h-6 w-full max-w-[320px] items-center justify-center gap-1.5 rounded-md bg-canvas/60 px-3">
          <svg viewBox="0 0 16 16" className="size-3 text-fg-3" aria-hidden>
            <rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
            <path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" strokeWidth="1.3" />
          </svg>
          <span className="truncate font-mono text-[11px] text-fg-3">{url}</span>
        </div>
      </div>
      <div className="relative">{children}</div>
    </div>
  );
}

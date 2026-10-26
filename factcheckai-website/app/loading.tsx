import LogoLoader from '@/components/LogoLoader';

export default function Loading() {
  return (
    // Hidden for the first 150 ms: most pages are ready by then, and a loader that
    // flashes for an instant feels slower than none at all.
    <div className="flex min-h-[100svh] items-center justify-center bg-canvas opacity-0 [animation:loader-in_.2s_ease-out_.15s_forwards]">
      <LogoLoader className="h-auto w-[min(42vw,180px)] [--tvl-start:.15s]" />
    </div>
  );
}

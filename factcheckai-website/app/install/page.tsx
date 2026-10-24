'use client';

import { useRef, useState } from 'react';
import { motion, useInView } from 'motion/react';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import MotionProvider from '@/components/landing/MotionProvider';
import { EASE_OUT, EASE_OUT_EXPO, Mark, Reveal, TextLink } from '@/components/landing/primitives';
import { GITHUB_URL } from '@/components/landing/data';

const ZIP_URL = '/truvanta-v2.6.2.zip';
const VERSION = '2.6.2';

const STEPS: { title: string; text: React.ReactNode; visual: React.ReactNode }[] = [
  {
    title: 'Unzip the download.',
    text: 'Extract it to a folder you’ll keep. The browser loads Truvanta from that folder, so don’t delete it afterwards.',
    visual: <UnzipVisual />,
  },
  {
    title: 'Open the extensions page.',
    text: 'Paste this into the address bar. In Edge, use edge://extensions instead.',
    visual: <CopyField value="chrome://extensions" />,
  },
  {
    title: 'Turn on Developer mode.',
    text: 'The switch is in the top-right corner of the extensions page.',
    visual: <ToggleVisual />,
  },
  {
    title: 'Click Load unpacked.',
    text: 'Choose the folder you extracted: the one that contains manifest.json.',
    visual: <LoadVisual />,
  },
  {
    title: 'Pin it to your toolbar.',
    text: 'Click the puzzle icon next to the address bar, then the pin beside TruvantaAI.',
    visual: <PinVisual />,
  },
];

export default function InstallPage() {
  return (
    <MotionProvider>
      <Header />
      <main>
        <section className="pt-[clamp(128px,16vh,176px)] pb-[clamp(72px,8vw,112px)]">
          <div className="container-page flex flex-col items-center text-center">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.9, ease: EASE_OUT_EXPO }}
              className="flex flex-col items-center"
            >
              <Mark className="h-12 w-auto" />
              <h1 className="mt-8 text-display text-fg">Install Truvanta.</h1>
              <p className="mt-5 max-w-[34rem] text-lead text-fg-2">
                Truvanta isn’t in the Chrome Web Store yet, so you add it in developer mode. It takes
                about a minute.
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.2 }}
              className="mt-10 flex flex-col items-center gap-4"
            >
              <a
                href={ZIP_URL}
                download
                className="inline-flex h-12 items-center gap-2.5 rounded-full bg-accent px-6 text-[15px] font-medium tracking-[-0.01em] text-on-accent transition-[background-color,transform] duration-150 ease-out hover:bg-accent-hover active:scale-[0.97]"
              >
                <svg viewBox="0 0 16 16" fill="none" aria-hidden className="size-4">
                  <path d="M8 2.5v8m0 0L4.5 7M8 10.5 11.5 7M3 13.5h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Download extension
              </a>
              <p className="font-mono text-[12px] text-fg-3">
                v{VERSION} · ZIP · Chrome, Edge, Brave
              </p>
            </motion.div>
          </div>
        </section>

        <section className="pb-[clamp(96px,10vw+40px,176px)]">
          <div className="container-page">
            <ol className="mx-auto max-w-[960px] border-t border-line">
              {STEPS.map((step, i) => (
                <li key={step.title} className="border-b border-line">
                  <Reveal className="grid gap-8 py-12 md:grid-cols-[64px_1fr_minmax(0,380px)] md:items-start md:gap-10">
                    <span className="font-mono text-[13px] text-fg-3 md:pt-3">0{i + 1}</span>
                    <div>
                      <h2 className="text-title text-fg">{step.title}</h2>
                      <p className="mt-3 max-w-[26rem] text-body text-fg-2">{step.text}</p>
                    </div>
                    <div>{step.visual}</div>
                  </Reveal>
                </li>
              ))}
            </ol>

            <Reveal className="mx-auto mt-24 flex max-w-[40rem] flex-col items-center text-center">
              <h2 className="text-display text-fg">You’re set.</h2>
              <p className="mt-5 text-lead text-fg-2">
                Highlight any sentence, right-click, and choose{' '}
                <span className="text-fg">TruthScan with TruvantaAI</span>. Or press{' '}
                <kbd className="rounded-md border border-line-strong bg-panel px-1.5 py-0.5 font-mono text-[0.8em] text-fg">
                  Ctrl+Shift+U
                </kbd>
                .
              </p>
              <div className="mt-10 flex flex-col items-center gap-4 text-[15px] sm:flex-row sm:gap-8">
                <TextLink href="/support">Something not working?</TextLink>
                <TextLink href={`${GITHUB_URL}/issues`} external>
                  Report an issue on GitHub
                </TextLink>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <Footer />
    </MotionProvider>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return <div className="elevated rounded-[16px] bg-panel p-4">{children}</div>;
}

function FolderIcon({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden className={className}>
      <path d="M2.5 5.5a1.5 1.5 0 0 1 1.5-1.5h3.6l1.6 1.8H16a1.5 1.5 0 0 1 1.5 1.5v7.2A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

function UnzipVisual() {
  return (
    <Panel>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3 rounded-[10px] bg-canvas/60 px-3 py-2.5">
          <span className="grid size-7 place-items-center rounded-[7px] bg-panel-2 font-mono text-[9px] text-fg-2">ZIP</span>
          <span className="truncate font-mono text-[12px] text-fg-2">truvanta-v2.6.2.zip</span>
        </div>
        <div className="flex justify-center text-fg-3" aria-hidden>
          <svg viewBox="0 0 16 16" fill="none" className="size-4">
            <path d="M8 3v10m0 0-3.5-3.5M8 13l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div className="flex items-center gap-3 rounded-[10px] bg-canvas/60 px-3 py-2.5">
          <FolderIcon className="size-7 text-accent" />
          <span className="truncate font-mono text-[12px] text-fg">truvantaai-extension/</span>
        </div>
      </div>
    </Panel>
  );
}

function CopyField({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Panel>
      <div className="flex items-center gap-2 rounded-[10px] bg-canvas/60 py-1.5 pl-3 pr-1.5">
        <svg viewBox="0 0 16 16" className="size-3.5 shrink-0 text-fg-3" aria-hidden>
          <rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
          <path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" strokeWidth="1.3" />
        </svg>
        <code className="flex-1 truncate font-mono text-[13px] text-fg">{value}</code>
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            } catch {
              /* clipboard unavailable */
            }
          }}
          className="h-8 min-w-[64px] rounded-[8px] bg-panel-2 px-3 text-[12px] font-medium text-fg-2 transition-colors duration-150 hover:text-fg active:scale-[0.97]"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </Panel>
  );
}

function ToggleVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const on = useInView(ref, { once: true, amount: 0.8 });
  return (
    <div ref={ref}>
      <Panel>
        <div className="flex items-center justify-between rounded-[10px] bg-canvas/60 px-3 py-3">
          <span className="text-[13px] text-fg">Developer mode</span>
          <span
            className={`relative h-6 w-10 rounded-full transition-colors duration-300 delay-300 ${on ? 'bg-accent' : 'bg-panel-2'}`}
          >
            <motion.span
              className="absolute top-1 left-1 size-4 rounded-full bg-fg shadow-sm"
              animate={{ x: on ? 16 : 0 }}
              transition={{ duration: 0.3, ease: EASE_OUT, delay: 0.3 }}
            />
          </span>
        </div>
      </Panel>
    </div>
  );
}

function LoadVisual() {
  return (
    <Panel>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-[8px] border border-accent/60 px-3 py-1.5 text-[12px] font-medium text-accent">
          Load unpacked
        </span>
        <span className="rounded-[8px] border border-line-strong px-3 py-1.5 text-[12px] text-fg-3">Pack extension</span>
        <span className="rounded-[8px] border border-line-strong px-3 py-1.5 text-[12px] text-fg-3">Update</span>
      </div>
      <div className="mt-3 flex items-center gap-3 rounded-[10px] bg-canvas/60 px-3 py-2.5">
        <FolderIcon className="size-5 text-fg-2" />
        <span className="flex-1 truncate font-mono text-[12px] text-fg">truvantaai-extension/</span>
        <span className="font-mono text-[11px] text-fg-3">manifest.json</span>
      </div>
    </Panel>
  );
}

function PinVisual() {
  return (
    <Panel>
      <div className="flex items-center gap-3 rounded-[10px] bg-canvas/60 px-3 py-2.5">
        <span className="h-6 flex-1 rounded-full bg-panel-2" aria-hidden />
        <span className="grid size-7 place-items-center rounded-full bg-white/[0.08]">
          <Mark pixels={false} className="h-3.5 w-auto" />
        </span>
        <svg viewBox="0 0 20 20" fill="none" aria-hidden className="size-5 text-fg-2">
          <path d="M8 3.5a1.5 1.5 0 0 1 3 0V5h3a1 1 0 0 1 1 1v3h-1.5a1.5 1.5 0 0 0 0 3H15v3a1 1 0 0 1-1 1h-3v-1.5a1.5 1.5 0 0 0-3 0V16H5a1 1 0 0 1-1-1v-3h1.5a1.5 1.5 0 0 0 0-3H4V6a1 1 0 0 1 1-1h3z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="mt-2 flex items-center justify-between rounded-[10px] px-3 py-2">
        <span className="flex items-center gap-2.5 text-[13px] text-fg">
          <Mark pixels={false} className="h-3.5 w-auto" />
          TruvantaAI
        </span>
        <svg viewBox="0 0 16 16" aria-hidden className="size-4 text-accent">
          <path d="M9.6 2.2 13.8 6.4l-1.2.4-2.4 2.4.2 2.6-1 1-2.4-2.4L3.4 14l-.4-.4 3.6-3.6-2.4-2.4 1-1 2.6.2 2.4-2.4z" fill="currentColor" />
        </svg>
      </div>
    </Panel>
  );
}

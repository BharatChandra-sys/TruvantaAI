'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView, useReducedMotion } from 'motion/react';
import BrowserFrame from './BrowserFrame';
import ExtensionPopup from './ExtensionPopup';
import { EASE_IN_OUT, EASE_OUT, EASE_OUT_EXPO, EASE_SHEET, PillLink, TextLink } from './primitives';
import { CHECKS, INSTALL_URL } from './data';

type Phase = 'idle' | 'highlight' | 'loading' | 'result';

// Time spent in each phase before moving to the next one (ms).
const TIMELINE: Record<Phase, { next: Phase; ms: number }> = {
  idle: { next: 'highlight', ms: 900 },
  highlight: { next: 'loading', ms: 800 },
  loading: { next: 'result', ms: 1500 },
  result: { next: 'idle', ms: 4200 },
};

const HEADLINE = ['Know', 'what’s', 'true.'];

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-[clamp(128px,18vh,184px)] pb-[clamp(80px,10vw,140px)]">
      <div className="container-page">
        <div className="mx-auto flex max-w-[860px] flex-col items-center text-center">
          <h1 className="text-display-xl text-fg">
            <span className="sr-only">Know what’s true.</span>
            <span aria-hidden className="inline-flex flex-wrap justify-center gap-x-[0.25em]">
              {HEADLINE.map((word, i) => (
                <span key={word} className="inline-block overflow-hidden pb-[0.08em] -mb-[0.08em]">
                  <motion.span
                    className="inline-block"
                    initial={{ y: '105%' }}
                    animate={{ y: 0 }}
                    transition={{ duration: 0.9, ease: EASE_OUT_EXPO, delay: 0.1 + i * 0.08 }}
                  >
                    {word}
                  </motion.span>
                </span>
              ))}
            </span>
          </h1>

          <motion.div
            className="flex flex-col items-center"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.35 }}
          >
            <p className="mt-6 max-w-[34rem] text-lead text-fg-2">
              Highlight any sentence on the web. Truvanta checks it against real sources and tells you
              how sure it is.
            </p>
            <div className="mt-10 flex flex-col items-center gap-5 sm:flex-row sm:gap-7">
              <PillLink href={INSTALL_URL}>Get the extension, free</PillLink>
              <TextLink href="#how-it-works" className="text-[15px]">
                See how it works
              </TextLink>
            </div>
            <p className="mt-5 text-caption text-fg-3">For Chrome, Edge and Brave.</p>
          </motion.div>
        </div>

        <motion.div
          className="mx-auto mt-[clamp(56px,7vw,88px)] max-w-[1080px]"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: EASE_OUT_EXPO, delay: 0.45 }}
        >
          <HeroDemo />
        </motion.div>
      </div>
    </section>
  );
}

function HeroDemo() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.35 });
  const reduce = useReducedMotion();
  const [phase, setPhase] = useState<Phase>('idle');

  useEffect(() => {
    if (reduce || !inView) return;
    const t = setTimeout(() => setPhase(TIMELINE[phase].next), TIMELINE[phase].ms);
    return () => clearTimeout(t);
  }, [phase, inView, reduce]);

  const shown: Phase = reduce ? 'result' : phase;
  const marked = shown !== 'idle';
  const popupOpen = shown === 'loading' || shown === 'result';

  return (
    <div ref={ref}>
      <BrowserFrame url="news.example.com/climate/mauna-loa">
        <div className="relative h-[700px] overflow-hidden sm:h-[500px]">
          <Article marked={marked} />
          <AnimatePresence>
            {popupOpen && (
              <motion.div
                key="popup"
                className="absolute inset-x-4 bottom-4 flex justify-center sm:inset-x-auto sm:right-8 sm:bottom-8 lg:right-12"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12, transition: { duration: 0.3, ease: EASE_OUT } }}
                transition={{ duration: 0.5, ease: EASE_SHEET }}
              >
                <ExtensionPopup check={CHECKS.true} phase={shown === 'result' ? 'result' : 'loading'} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </BrowserFrame>
    </div>
  );
}

function Article({ marked }: { marked: boolean }) {
  return (
    <article className="px-6 pt-8 sm:px-10 sm:pt-12 lg:px-14">
      <div className="max-w-[540px]">
        <p className="text-caption text-fg-3">Climate · 4 min read</p>
        <h3 className="mt-3 text-[22px] font-semibold leading-[1.2] tracking-[-0.02em] text-fg sm:text-[26px]">
          What the latest Mauna Loa readings tell us
        </h3>
        <p className="mt-5 text-[15px] leading-[1.7] text-fg-2">
          Scientists have tracked carbon dioxide on the slopes of Hawaii’s largest volcano since 1958.{' '}
          <Highlight on={marked}>Atmospheric CO₂ has passed 420 ppm at Mauna Loa,</Highlight> a level the
          planet has not seen in millions of years. The yearly increase has also grown faster.
        </p>
        <div className="mt-6 hidden flex-col gap-3 sm:flex" aria-hidden>
          <span className="h-2 w-full rounded-full bg-panel-2" />
          <span className="h-2 w-[92%] rounded-full bg-panel-2" />
          <span className="h-2 w-[80%] rounded-full bg-panel-2" />
          <span className="h-2 w-[86%] rounded-full bg-panel-2" />
        </div>
      </div>
    </article>
  );
}

export function Highlight({ on, children }: { on: boolean; children: React.ReactNode }) {
  return (
    <motion.mark
      className="rounded-[3px] bg-no-repeat text-fg"
      style={{
        backgroundColor: 'transparent',
        backgroundImage: 'linear-gradient(rgb(255 197 61 / 0.26), rgb(255 197 61 / 0.26))',
      }}
      initial={false}
      animate={{ backgroundSize: on ? '100% 100%' : '0% 100%' }}
      transition={{ duration: on ? 0.6 : 0.3, ease: on ? EASE_IN_OUT : EASE_OUT }}
    >
      {children}
    </motion.mark>
  );
}

'use client';

import { useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from 'motion/react';
import BrowserFrame from './BrowserFrame';
import ExtensionPopup from './ExtensionPopup';
import { Highlight } from './Hero';
import { EASE_OUT, EASE_SHEET, Mark, Reveal } from './primitives';
import { CHECKS } from './data';

const STEPS = [
  { title: 'Select.', text: 'Highlight a sentence, or right-click any claim on the page.' },
  { title: 'Check.', text: 'Truvanta searches trusted sources and weighs what each one says.' },
  { title: 'Know.', text: 'A clear verdict, how confident it is, and links you can open.' },
];

export default function Walkthrough() {
  return (
    <section id="how-it-works" className="scroll-mt-16 pt-[clamp(96px,10vw+40px,176px)]">
      <div className="container-page">
        <Reveal className="max-w-[40rem]">
          <h2 className="text-display text-fg">Works where you read.</h2>
          <p className="mt-5 text-lead text-fg-2">
            Nothing to copy, no new tab to open. Truvanta sits in your browser and answers in place.
          </p>
        </Reveal>
      </div>

      {/* Pinned, scroll-driven version: large screens with motion allowed */}
      <div className="hidden lg:motion-safe:block">
        <Pinned />
      </div>

      {/* Stacked version: phones, tablets, reduced motion */}
      <div className="container-page mt-16 flex flex-col gap-20 pb-[clamp(96px,10vw+40px,176px)] lg:motion-safe:hidden">
        {STEPS.map((step, i) => (
          <Reveal key={step.title} className="flex flex-col gap-6">
            <div>
              <h3 className="text-title text-fg">{step.title}</h3>
              <p className="mt-2 max-w-[28rem] text-body text-fg-2">{step.text}</p>
            </div>
            <Stage step={i} compact />
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function Pinned() {
  const ref = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] });

  useMotionValueEvent(scrollYProgress, 'change', (p) => {
    setStep(p < 0.34 ? 0 : p < 0.67 ? 1 : 2);
  });

  return (
    <div ref={ref} className="relative h-[280vh]">
      <div className="sticky top-0 flex h-screen items-center">
        <div className="container-page grid grid-cols-12 items-center gap-6">
          <div className="col-span-4 flex gap-8">
            <div className="relative w-px self-stretch bg-line" aria-hidden>
              <motion.div
                className="absolute inset-x-0 top-0 h-full origin-top bg-fg"
                style={{ scaleY: scrollYProgress }}
              />
            </div>
            <ol className="flex flex-col gap-12 py-2">
              {STEPS.map((s, i) => (
                <li
                  key={s.title}
                  className={`transition-opacity duration-300 ease-out ${i === step ? 'opacity-100' : 'opacity-35'}`}
                  aria-current={i === step ? 'step' : undefined}
                >
                  <h3 className="text-title text-fg">{s.title}</h3>
                  <p className="mt-2 max-w-[22rem] text-body text-fg-2">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
          <div className="col-span-8">
            <Stage step={step} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stage({ step, compact = false }: { step: number; compact?: boolean }) {
  const check = CHECKS.false;
  return (
    <BrowserFrame url="travel.example.com/great-wall-guide">
      <div className={`relative overflow-hidden ${compact ? 'h-[680px] sm:h-[620px]' : 'h-[640px]'}`}>
        <article className="px-6 pt-8 sm:px-10 sm:pt-10">
          <div className="max-w-[460px]">
            <p className="text-caption text-fg-3">Travel · Guide</p>
            <h4 className="mt-3 text-[22px] font-semibold leading-[1.2] tracking-[-0.02em] text-fg">
              Ten things to know before visiting the Great Wall
            </h4>
            <p className="mt-5 text-[15px] leading-[1.7] text-fg-2">
              Stretching across northern China, the wall took more than two thousand years to build.{' '}
              <Highlight on>{check.claim.replace(/\.$/, ',')}</Highlight> our guide told us on the
              first morning.
            </p>
          </div>

          <div className="relative mt-5 h-[340px]">
            <AnimatePresence>
              {step === 0 && (
                <motion.div
                  key="menu"
                  className="absolute left-10 top-0 w-[240px] sm:left-24"
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.15 } }}
                  transition={{ duration: 0.2, ease: EASE_OUT }}
                >
                  <ContextMenu />
                </motion.div>
              )}
              {step > 0 && (
                <motion.div
                  key="popup"
                  className="absolute inset-x-0 top-0"
                  initial={{ opacity: 0, y: 28 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 12, transition: { duration: 0.25, ease: EASE_OUT } }}
                  transition={{ duration: 0.5, ease: EASE_SHEET }}
                >
                  <ExtensionPopup check={check} phase={step === 1 ? 'loading' : 'result'} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </article>

      </div>
    </BrowserFrame>
  );
}

function ContextMenu() {
  return (
    <span className="elevated block rounded-[10px] bg-panel-2 p-1 text-[13px] leading-none">
      <span className="block px-2.5 py-2 text-fg-3">Copy</span>
      <span className="block px-2.5 py-2 text-fg-3">Search the web</span>
      <span className="my-1 block h-px bg-line" />
      <span className="flex items-center justify-between rounded-[7px] bg-white/[0.06] px-2.5 py-2 text-fg">
        <span className="flex items-center gap-2">
          <Mark pixels={false} className="h-3 w-auto" />
          TruthScan with TruvantaAI
        </span>
        <span className="hidden font-mono text-[11px] text-fg-3 sm:inline">Ctrl+Shift+U</span>
      </span>
    </span>
  );
}

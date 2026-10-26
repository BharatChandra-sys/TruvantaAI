'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView, useReducedMotion } from 'motion/react';
import { Reveal, EASE_OUT_EXPO } from './primitives';

// A real check, replayed with the timings it ran with (local backend, October 2026).
const CLAIM = 'Mount Kilimanjaro is located in Kenya.';
const EARLY = 'Mount Kilimanjaro is located in Tanzania, not Kenya.';
const FINAL =
  'Mount Kilimanjaro is located in Tanzania, not Kenya. [1] states that the Kilimanjaro massif is in Tanzania. [2] confirms Kilimanjaro is an administrative region of Tanzania.';
const SOURCES = [
  { name: 'Wikipedia', domain: 'en.wikipedia.org', at: 1.15 },
  { name: 'Wikipedia', domain: 'en.wikipedia.org', at: 1.24 },
  { name: 'MSN', domain: 'msn.com', at: 1.3 },
  { name: 'eTurboNews', domain: 'eturbonews.com', at: 1.55 },
];
const EARLY_AT = 1.1;
const VERDICT_AT = 2.2;
const END = VERDICT_AT;
const HOLD_S = 5;

const STEPS = [
  { at: EARLY_AT, label: 'Early answer', text: 'From established knowledge, while the search runs.' },
  { at: 1.15, label: 'Sources arrive', text: 'Fact-checks, news, reference and research, in parallel.' },
  { at: VERDICT_AT, label: 'Sourced verdict', text: 'Read from the sources, each statement cited.' },
];

export default function LiveCheck() {
  const stage = useRef<HTMLDivElement>(null);
  const inView = useInView(stage, { amount: 0.4 });
  const reduce = useReducedMotion();
  const [t, setT] = useState(0);

  // Real-time clock while the card is on screen; holds on the result, then replays.
  useEffect(() => {
    if (reduce) {
      setT(END);
      return;
    }
    if (!inView) return;
    let raf = 0;
    let start = performance.now() - t * 1000;
    const tick = (now: number) => {
      let s = (now - start) / 1000;
      if (s > END + HOLD_S) {
        start = now;
        s = 0;
      }
      setT(s);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, reduce]);

  const shown = Math.min(t, END);
  const early = t >= EARLY_AT;
  const done = t >= VERDICT_AT;
  const sources = SOURCES.filter((s) => t >= s.at);

  return (
    <section className="section-y" aria-labelledby="live-title">
      <div className="container-page grid items-center gap-14 lg:grid-cols-12 lg:gap-6">
        <Reveal className="lg:col-span-5">
          <h2 id="live-title" className="text-display text-fg">
            An answer in a second. Then the proof.
          </h2>
          <p className="mt-5 max-w-[30rem] text-lead text-fg-2">
            You see an early answer almost at once. Sources stream in under it, and the verdict
            they support replaces it, saying whether the early answer held up.
          </p>
          <ol className="mt-10 flex flex-col gap-5">
            {STEPS.map((s) => {
              const reached = t >= s.at;
              return (
                <li key={s.label} className="flex gap-4">
                  <span
                    className={`mt-[3px] w-12 shrink-0 font-mono text-[13px] tabular-nums transition-colors duration-300 ${
                      reached ? 'text-accent' : 'text-fg-3'
                    }`}
                  >
                    {s.at.toFixed(1)} s
                  </span>
                  <span>
                    <span
                      className={`block text-[16px] font-semibold tracking-[-0.01em] transition-colors duration-300 ${
                        reached ? 'text-fg' : 'text-fg-3'
                      }`}
                    >
                      {s.label}
                    </span>
                    <span className="mt-1 block text-body text-fg-2">{s.text}</span>
                  </span>
                </li>
              );
            })}
          </ol>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-6 lg:col-start-7">
          <div ref={stage} className="mx-auto w-full max-w-[420px]">
            <div className="mb-3 flex items-center justify-between px-1">
              <span className="text-caption text-fg-3">Replay of a real check, timed as it ran</span>
              <span className="font-mono text-[13px] tabular-nums text-fg-2" aria-hidden>
                {shown.toFixed(1)} s
              </span>
            </div>

            <div className="elevated rounded-[16px] bg-panel p-5" aria-live="off">
              <p className="border-l-2 border-line-strong pl-3 text-[14px] leading-[1.45] text-fg-2">
                {CLAIM}
              </p>

              <div className="mt-4 min-h-[118px]">
                <AnimatePresence mode="wait" initial={false}>
                  {!early && (
                    <motion.div
                      key="search"
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="flex items-center gap-2 text-[13px] text-fg-2"
                    >
                      <span className="size-1.5 animate-pulse rounded-full bg-fg-2" />
                      Searching sources
                    </motion.div>
                  )}
                  {early && !done && (
                    <motion.div
                      key="early"
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3, ease: EASE_OUT_EXPO }}
                      className="rounded-[10px] bg-canvas/50 p-3 shadow-[inset_0_0_0_1px_var(--color-line)]"
                    >
                      <div className="flex items-center justify-between">
                        <Chip />
                        <span className="font-mono text-[11px] text-fg-3">early answer · 70%</span>
                      </div>
                      <p className="mt-2 text-[13px] leading-[1.5] text-fg-2">{EARLY}</p>
                    </motion.div>
                  )}
                  {done && (
                    <motion.div
                      key="final"
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, ease: EASE_OUT_EXPO }}
                    >
                      <div className="flex items-center justify-between">
                        <Chip />
                        <span className="font-mono text-[12px] text-fg-2">97% confidence</span>
                      </div>
                      <div className="mt-3 h-[3px] overflow-hidden rounded-full bg-panel-2">
                        <motion.div
                          className="h-full origin-left rounded-full bg-false"
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: 0.97 }}
                          transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
                        />
                      </div>
                      <p className="mt-3 text-[13px] leading-[1.5] text-fg-2">{FINAL}</p>
                      <p className="mt-2 text-[12px] text-fg-3">Early answer confirmed by 4 sources.</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="mt-4 flex flex-col gap-1.5">
                {SOURCES.map((s, i) => {
                  const here = sources.includes(s);
                  return (
                    <div key={i} className="relative h-9 overflow-hidden rounded-[8px] bg-canvas/50">
                      <AnimatePresence initial={false}>
                        {here ? (
                          <motion.div
                            key="row"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.26, ease: EASE_OUT_EXPO }}
                            className="absolute inset-0 flex items-center gap-2.5 px-2.5"
                          >
                            <span className="grid size-5 place-items-center rounded-[5px] bg-panel-2 text-[10px] font-semibold text-fg-2">
                              {done ? i + 1 : s.name[0]}
                            </span>
                            <span className="truncate text-[12px] text-fg">{s.name}</span>
                            <span className="ml-auto shrink-0 font-mono text-[11px] text-fg-3">{s.domain}</span>
                          </motion.div>
                        ) : (
                          <motion.span
                            key="skel"
                            exit={{ opacity: 0, transition: { duration: 0.08 } }}
                            className="absolute left-2.5 top-1/2 h-2 -translate-y-1/2 rounded-full bg-panel-2"
                            style={{ width: `${[62, 48, 70, 54][i]}%` }}
                          />
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Chip() {
  return (
    <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-false/12 px-2.5 text-[12px] font-medium text-false">
      <i className="size-1.5 rounded-full bg-current" />
      False
    </span>
  );
}

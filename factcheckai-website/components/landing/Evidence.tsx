'use client';

import dynamic from 'next/dynamic';
import { useRef, useState } from 'react';
import { motion, useInView, useScroll } from 'motion/react';
import { Reveal, EASE_OUT_EXPO } from './primitives';
import { VerdictChip } from './ExtensionPopup';
import { CHECKS } from './data';

const EvidenceScene = dynamic(() => import('./EvidenceScene'), { ssr: false });

const POINTS = [
  {
    title: 'Real sources.',
    text: 'Research journals, news wires and public data from agencies like NOAA and the WHO.',
  },
  {
    title: 'Checked citations.',
    text: 'Every link is verified before it’s shown to you, so a source can’t be made up.',
  },
  {
    title: 'Memory.',
    text: 'Claims that were checked before come back in seconds, with the same sources.',
  },
];

function supports3D() {
  if (typeof window === 'undefined') return false;
  if (!window.matchMedia('(min-width: 768px)').matches) return false;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  if ((navigator.hardwareConcurrency ?? 8) < 4) return false;
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch {
    return false;
  }
}

export default function Evidence() {
  const stage = useRef<HTMLDivElement>(null);
  const near = useInView(stage, { margin: '100% 0px 100% 0px', once: true });
  const visible = useInView(stage, { margin: '10% 0px 10% 0px' });
  const { scrollYProgress } = useScroll({ target: stage, offset: ['start end', 'end start'] });
  const [enabled, setEnabled] = useState(supports3D);
  const [ready, setReady] = useState(false);

  return (
    <section className="section-y relative bg-raised">
      <div className="container-page">
        <Reveal className="mx-auto max-w-[44rem] text-center">
          <h2 className="text-display text-fg">
            Every verdict shows
            <br className="hidden sm:inline" /> its work.
          </h2>
          <p className="mt-4 text-lead text-fg-2 leading-relaxed sm:mt-5">
            Truvanta reads widely, sets aside weak sources, and shows you the ones that decided the
            answer.
          </p>
        </Reveal>
      </div>

      <div ref={stage} className="relative mx-auto mt-8 h-[clamp(380px,70vh,680px)] max-w-[1400px] sm:mt-12">
        <motion.div
          className="absolute inset-0"
          animate={{ opacity: ready ? 0 : 1 }}
          transition={{ duration: 0.3 }}
        >
          <EvidenceStatic />
        </motion.div>
        {enabled && near && (
          <div className="absolute inset-0">
            <EvidenceScene
              progress={scrollYProgress}
              active={visible}
              onReady={() => setReady(true)}
              onFallback={() => {
                setReady(false);
                setEnabled(false);
              }}
            />
          </div>
        )}
      </div>

      <div className="container-page mt-8 sm:mt-12">
        <Reveal className="grid gap-6 border-t border-line pt-8 sm:gap-10 sm:pt-10 md:grid-cols-3 md:gap-8">
          {POINTS.map((p) => (
            <div key={p.title} className="flex flex-col gap-2">
              <h3 className="text-lg font-semibold tracking-[-0.01em] text-fg sm:text-[17px]">{p.title}</h3>
              <p className="max-w-[22rem] text-body text-fg-2 leading-relaxed">{p.text}</p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

// The scene drawn in DOM: shown on phones, with reduced motion, without WebGL,
// and while the 3D scene loads. Scattered sources drift in, the verdict card
// rises out of them and its evidence fills in.
const SCATTER = [
  [8, 18, -8, 0.5], [16, 64, 6, 0.35], [24, 30, 12, 0.4], [78, 22, -10, 0.45], [86, 60, 8, 0.35],
  [70, 78, -4, 0.3], [30, 82, 10, 0.3], [92, 36, 14, 0.25], [4, 46, 4, 0.25], [62, 8, -6, 0.3],
  [40, 6, 8, 0.2], [96, 82, -12, 0.2],
] as const;

function EvidenceStatic() {
  const ref = useRef<HTMLDivElement>(null);
  const shown = useInView(ref, { once: true, amount: 0.35 });
  return (
    <div ref={ref} className="relative h-full w-full overflow-hidden" aria-hidden>
      {SCATTER.map(([x, y, r, o], i) => (
        <motion.span
          key={i}
          className="absolute -ml-[42px] -mt-[26px] h-[52px] w-[84px]"
          style={{ left: `${x}%`, top: `${y}%` }}
          initial={{ opacity: 0, rotate: r * 3, scale: 0.7, x: (x - 50) * 1.6, y: (y - 50) * 1.2 }}
          animate={shown ? { opacity: o, rotate: r, scale: 1, x: 0, y: 0 } : undefined}
          transition={{ duration: 1.1, ease: EASE_OUT_EXPO, delay: i * 0.04 }}
        >
          <span
            className="evidence-bob block h-full w-full rounded-[8px] border border-white/40 bg-panel"
            style={{ animationDuration: `${5 + (i % 4)}s`, animationDelay: `${(i % 5) * -1.1}s` }}
          />
        </motion.span>
      ))}
      <motion.div
        className="absolute left-1/2 top-1/2 w-[min(78vw,380px)] -translate-x-1/2 -translate-y-1/2"
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={shown ? { opacity: 1, y: 0, scale: 1 } : undefined}
        transition={{ duration: 0.9, ease: EASE_OUT_EXPO, delay: 0.45 }}
      >
        <span className="absolute inset-0 translate-x-2 translate-y-2 rotate-[1.5deg] rounded-[16px] border border-white/15 bg-panel" />
        <span className="absolute inset-0 translate-x-1 translate-y-1 -rotate-1 rounded-[16px] border border-white/20 bg-panel" />
        <div className="relative rounded-[16px] border border-accent bg-panel p-5">
          <div className="flex items-center justify-between">
            <VerdictChip check={CHECKS.true} />
            <span className="font-mono text-[12px] text-fg-2">97% confidence</span>
          </div>
          <div className="mt-3 h-[3px] overflow-hidden rounded-full bg-panel-2">
            <motion.div
              className="h-full origin-left rounded-full bg-true"
              initial={{ scaleX: 0 }}
              animate={shown ? { scaleX: 0.97 } : undefined}
              transition={{ duration: 0.8, ease: EASE_OUT_EXPO, delay: 1.0 }}
            />
          </div>
          <div className="mt-4 flex flex-col gap-2">
            <span className="h-2 w-[86%] rounded-full bg-panel-2" />
            <span className="h-2 w-[72%] rounded-full bg-panel-2" />
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            {CHECKS.true.sources.map((s, i) => (
              <motion.div
                key={s.domain}
                className="flex items-center gap-2.5 rounded-[8px] bg-canvas/50 px-2.5 py-2"
                initial={{ opacity: 0, y: 6 }}
                animate={shown ? { opacity: 1, y: 0 } : undefined}
                transition={{ duration: 0.4, ease: EASE_OUT_EXPO, delay: 1.2 + i * 0.12 }}
              >
                <span className="grid size-5 place-items-center rounded-[5px] bg-panel-2 text-[10px] font-semibold text-fg-2">
                  {s.name[0]}
                </span>
                <span className="truncate text-[12px] text-fg">{s.name}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
}

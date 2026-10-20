'use client';

import dynamic from 'next/dynamic';
import { useRef, useState } from 'react';
import { motion, useInView, useScroll } from 'motion/react';
import { Reveal } from './primitives';
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
          <h2 className="text-display text-fg">Every verdict shows its work.</h2>
          <p className="mt-5 text-lead text-fg-2">
            Truvanta reads widely, sets aside weak sources, and shows you the ones that decided the
            answer.
          </p>
        </Reveal>
      </div>

      <div ref={stage} className="relative mx-auto mt-12 h-[clamp(380px,70vh,680px)] max-w-[1400px]">
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

      <div className="container-page mt-12">
        <Reveal className="grid gap-10 border-t border-line pt-10 md:grid-cols-3 md:gap-8">
          {POINTS.map((p) => (
            <div key={p.title}>
              <h3 className="text-[17px] font-semibold tracking-[-0.01em] text-fg">{p.title}</h3>
              <p className="mt-2 max-w-[22rem] text-body text-fg-2">{p.text}</p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

// Resting state of the scene, drawn in DOM. Shown on phones, with reduced
// motion, without WebGL, and while the scene loads.
const SCATTER = [
  [8, 18, -8, 0.5], [16, 64, 6, 0.35], [24, 30, 12, 0.4], [78, 22, -10, 0.45], [86, 60, 8, 0.35],
  [70, 78, -4, 0.3], [30, 82, 10, 0.3], [92, 36, 14, 0.25], [4, 46, 4, 0.25], [62, 8, -6, 0.3],
  [40, 6, 8, 0.2], [96, 82, -12, 0.2],
] as const;

function EvidenceStatic() {
  return (
    <div className="relative h-full w-full overflow-hidden" aria-hidden>
      {SCATTER.map(([x, y, r, o], i) => (
        <span
          key={i}
          className="absolute h-[52px] w-[84px] rounded-[8px] border border-white/40 bg-panel"
          style={{ left: `${x}%`, top: `${y}%`, transform: `translate(-50%,-50%) rotate(${r}deg)`, opacity: o }}
        />
      ))}
      <div className="absolute left-1/2 top-1/2 w-[min(78vw,380px)] -translate-x-1/2 -translate-y-1/2">
        <span className="absolute inset-0 translate-x-2 translate-y-2 rotate-[1.5deg] rounded-[16px] border border-white/15 bg-panel" />
        <span className="absolute inset-0 translate-x-1 translate-y-1 -rotate-1 rounded-[16px] border border-white/20 bg-panel" />
        <div className="relative rounded-[16px] border border-accent bg-panel p-5">
          <div className="flex items-center justify-between">
            <VerdictChip check={CHECKS.true} />
            <span className="font-mono text-[12px] text-fg-2">97% confidence</span>
          </div>
          <div className="mt-3 h-[3px] rounded-full bg-panel-2">
            <div className="h-full w-[97%] rounded-full bg-true" />
          </div>
          <div className="mt-4 flex flex-col gap-2">
            <span className="h-2 w-[86%] rounded-full bg-panel-2" />
            <span className="h-2 w-[72%] rounded-full bg-panel-2" />
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            {CHECKS.true.sources.map((s) => (
              <div key={s.domain} className="flex items-center gap-2.5 rounded-[8px] bg-canvas/50 px-2.5 py-2">
                <span className="grid size-5 place-items-center rounded-[5px] bg-panel-2 text-[10px] font-semibold text-fg-2">
                  {s.name[0]}
                </span>
                <span className="truncate text-[12px] text-fg">{s.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

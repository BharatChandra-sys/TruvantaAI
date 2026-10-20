'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useReducedMotion } from 'motion/react';
import ExtensionPopup from './ExtensionPopup';
import { Reveal } from './primitives';
import { CHECKS, VERDICT_LABEL, type Verdict } from './data';

const ORDER: Verdict[] = ['true', 'unsure', 'false'];
const AUTO_MS = 5000;

export default function Verdicts() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.5 });
  const reduce = useReducedMotion();
  const [active, setActive] = useState<Verdict>('unsure');
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!inView || touched || reduce) return;
    const t = setTimeout(() => {
      setActive((v) => ORDER[(ORDER.indexOf(v) + 1) % ORDER.length]);
    }, AUTO_MS);
    return () => clearTimeout(t);
  }, [active, inView, touched, reduce]);

  return (
    <section className="section-y">
      <div className="container-page grid items-center gap-14 lg:grid-cols-12 lg:gap-6">
        <Reveal className="lg:col-span-5">
          <h2 className="text-display text-fg">Honest when it isn’t sure.</h2>
          <p className="mt-5 max-w-[30rem] text-lead text-fg-2">
            Some claims don’t have a clean answer. When the evidence is mixed, Truvanta says so, and
            tells you how confident it is, instead of guessing.
          </p>
        </Reveal>

        <Reveal ref={ref} delay={0.1} className="flex flex-col items-center gap-6 lg:col-span-6 lg:col-start-7">
          <div
            role="tablist"
            aria-label="Example verdicts"
            className="relative flex rounded-full bg-panel p-1"
          >
            {ORDER.map((v) => (
              <button
                key={v}
                role="tab"
                aria-selected={active === v}
                onClick={() => {
                  setTouched(true);
                  setActive(v);
                }}
                className={`relative h-9 rounded-full px-4 text-[14px] font-medium transition-colors duration-150 sm:px-5 ${
                  active === v ? 'text-fg' : 'text-fg-3 hover:text-fg-2'
                }`}
              >
                {active === v && (
                  <motion.span
                    layoutId="verdict-tab"
                    className="absolute inset-0 rounded-full bg-panel-2 shadow-[0_0_0_1px_rgb(255_255_255/0.06)]"
                    transition={{ type: 'spring', visualDuration: 0.35, bounce: 0 }}
                  />
                )}
                <span className="relative">{VERDICT_LABEL[v]}</span>
              </button>
            ))}
          </div>
          <div role="tabpanel" className="flex w-full justify-center">
            <ExtensionPopup check={CHECKS[active]} phase="result" className="max-w-[400px]" />
          </div>
          <p className="text-caption text-fg-3">Illustrative examples.</p>
        </Reveal>
      </div>
    </section>
  );
}

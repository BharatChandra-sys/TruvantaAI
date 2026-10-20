'use client';

import { useId, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { EASE_OUT, PillLink, Reveal } from './primitives';
import { INSTALL_URL } from './data';

const FAQS = [
  {
    q: 'Is it free?',
    a: 'Yes. Truvanta is free to install and free to use.',
  },
  {
    q: 'Which browsers does it work in?',
    a: 'Chrome, Edge, Brave and other Chromium browsers. For now you install it from a ZIP file in developer mode. The install page walks you through it in about a minute.',
  },
  {
    q: 'What do you store?',
    a: 'The claims that get checked, with their verdicts and sources, so repeat questions are answered faster. If you sign in, your history is kept with your account. We don’t run ads or sell data. The privacy policy has the details.',
  },
  {
    q: 'Can it be wrong?',
    a: 'Yes. No fact-checker is right every time. That’s why every verdict comes with its sources and a confidence level, so you can judge the evidence yourself.',
  },
  {
    q: 'Is it open source?',
    a: 'Yes. The extension, backend and models are on GitHub under the Apache 2.0 license.',
  },
];

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);
  const baseId = useId();

  return (
    <section id="faq" className="section-y scroll-mt-16 border-t border-line">
      <div className="container-page grid gap-12 lg:grid-cols-12 lg:gap-6">
        <Reveal className="lg:col-span-4">
          <h2 className="text-display text-fg">Questions.</h2>
        </Reveal>
        <Reveal delay={0.08} className="lg:col-span-7 lg:col-start-6">
          <ul className="border-t border-line">
            {FAQS.map((item, i) => {
              const isOpen = open === i;
              const panelId = `${baseId}-${i}`;
              return (
                <li key={item.q} className="border-b border-line">
                  <button
                    onClick={() => setOpen(isOpen ? null : i)}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    className="flex w-full items-center justify-between gap-6 py-6 text-left text-[19px] font-medium tracking-[-0.015em] text-fg transition-colors duration-150 hover:text-white"
                  >
                    {item.q}
                    <svg
                      viewBox="0 0 16 16"
                      aria-hidden
                      className={`size-4 shrink-0 text-fg-3 transition-transform duration-200 ease-out ${isOpen ? 'rotate-45' : ''}`}
                    >
                      <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        id={panelId}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: EASE_OUT }}
                        className="overflow-hidden"
                      >
                        <p className="max-w-[36rem] pb-6 text-body text-fg-2">{item.a}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </li>
              );
            })}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}

export function Closing() {
  return (
    <section className="pt-[clamp(120px,14vw,200px)] pb-[clamp(120px,14vw,200px)]">
      <Reveal className="container-page flex flex-col items-center text-center">
        <h2 className="text-display text-fg">Check your next claim.</h2>
        <PillLink href={INSTALL_URL} className="mt-10">
          Get the extension, free
        </PillLink>
      </Reveal>
    </section>
  );
}

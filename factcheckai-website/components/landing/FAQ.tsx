'use client';

import { useId, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { EASE_OUT, PillLink, Reveal } from './primitives';
import { INSTALL_URL } from './data';

const FAQS = [
  {
    q: 'Is it free?',
    a: 'Yes. Truvanta is free to install and free to use. No subscriptions, no premium tiers, no hidden costs.',
  },
  {
    q: 'Which browsers does it work in?',
    a: 'Chrome, Edge, Brave and other Chromium browsers. For now you install it from a ZIP file in developer mode. The install page walks you through it in about a minute.',
  },
  {
    q: 'How does it fact-check claims?',
    a: 'Truvanta searches published fact-checks, news, Wikipedia, and research databases in parallel. It scrapes the most relevant pages, extracts matching paragraphs, and an AI model reads only those passages to decide the verdict. Every source is linked so you can verify it yourself.',
  },
  {
    q: 'Can it be wrong?',
    a: 'Yes. No fact-checker is right every time. That's why every verdict comes with its sources and a confidence level, so you can judge the evidence yourself. When evidence is mixed or insufficient, it says "Uncertain" instead of guessing.',
  },
  {
    q: 'What do you store?',
    a: 'The claims that get checked, with their verdicts and sources, so repeat questions are answered faster. If you sign in, your history is kept with your account. We don't run ads or sell data. The privacy policy has the details.',
  },
  {
    q: 'Does it work in other languages?',
    a: 'Yes. Claims in other languages are normalized before searching. The system primarily searches English-language sources, but handles multilingual input.',
  },
  {
    q: 'How fast is it?',
    a: 'First sources appear in about half a second. A published fact-check match shows within a second. Full verdicts with evidence typically take 3-5 seconds. Repeat checks are instant thanks to caching.',
  },
  {
    q: 'Is it open source?',
    a: 'Yes. The extension, backend, ML models, and decision logic are on GitHub under the Apache 2.0 license. Every search source, every algorithm, every model weight is in the repository.',
  },
  {
    q: 'How do I know it's not biased?',
    a: 'Truvanta doesn't take sides. It searches both mainstream and alternative sources, shows you supporting and contradicting evidence, and marks each source's stance. The decision logic uses trained models plus evidence scoring—no editorial judgment.',
  },
  {
    q: 'Does it track my browsing?',
    a: 'No. The extension only sees text you explicitly select and check. It doesn't monitor page visits, read your tabs, or track your activity. Fact-check requests go to the backend, but your browsing history never does.',
  },
  {
    q: 'Can I use it for academic research?',
    a: 'Yes, but verify citations independently. Truvanta is designed for general fact-checking, not peer review. It searches PubMed for health claims and can find published research, but always check primary sources for academic work.',
  },
  {
    q: 'What if there's no verdict?',
    a: 'If Truvanta returns "Uncertain," it means the evidence was mixed, insufficient, or the claim isn't something that can be fact-checked (like opinions or future predictions). That's a feature, not a failure—uncertain is better than a wrong guess.',
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
                        <p className="max-w-[36rem] pb-6 text-body text-fg-2 leading-relaxed">{item.a}</p>
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

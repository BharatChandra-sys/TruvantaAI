'use client';

import { Reveal, TextLink } from './primitives';
import { GITHUB_URL } from './data';

const PRINCIPLES = [
  { 
    title: 'Every verdict links its sources', 
    description: 'Click any source to read what it actually says. No hidden reasoning.' 
  },
  { 
    title: 'Every source shows its stance', 
    description: 'Supporting, contradicting or neutral. You see both sides of the evidence.' 
  },
  { 
    title: 'Uncertain means uncertain', 
    description: 'Not a guess. When evidence is thin or mixed, the verdict says so.' 
  },
  { 
    title: 'Open source lets you verify', 
    description: 'Every search, every model, every decision rule is in the repository.' 
  },
];

export default function Measured() {
  return (
    <section className="section-y bg-raised" aria-labelledby="transparency-title">
      <div className="container-page">
        <Reveal className="max-w-[44rem]">
          <h2 id="transparency-title" className="text-display text-fg">
            Built for transparency,
            <br className="hidden sm:inline" /> not black boxes.
          </h2>
          <p className="mt-4 text-lead text-fg-2 sm:mt-5">
            Every step of fact-checking is visible and verifiable. No hidden models making invisible decisions.
          </p>
        </Reveal>

        <Reveal 
          delay={0.1} 
          className="mt-10 grid gap-6 border-t border-line pt-8 sm:mt-14 sm:grid-cols-2 sm:gap-8 sm:pt-10"
        >
          {PRINCIPLES.map((p, i) => (
            <div key={i} className="flex flex-col gap-2 sm:gap-3">
              <h3 className="text-xl font-semibold leading-tight tracking-[-0.02em] text-fg sm:text-[1.375rem]">
                {p.title}
              </h3>
              <p className="text-body text-fg-2 leading-relaxed">{p.description}</p>
            </div>
          ))}
        </Reveal>

        <Reveal 
          delay={0.15} 
          className="mt-8 flex flex-col gap-4 text-caption text-fg-3 sm:mt-12 sm:flex-row sm:items-center sm:gap-6"
        >
          <span className="leading-relaxed">
            Models trained on public datasets. Search sources documented. Decision logic in the code.
          </span>
          <TextLink href={GITHUB_URL} external className="self-start sm:self-auto">
            View on GitHub
          </TextLink>
        </Reveal>
      </div>
    </section>
  );
}

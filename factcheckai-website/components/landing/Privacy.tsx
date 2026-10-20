'use client';

import { useRef } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'motion/react';
import { TextLink } from './primitives';
import { GITHUB_URL } from './data';

const STATEMENT =
  'No ads. Nothing sold. The code is open, so you can read exactly what happens to every claim you check.';

export default function Privacy() {
  const ref = useRef<HTMLParagraphElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.85', 'end 0.45'] });
  const words = STATEMENT.split(' ');

  return (
    <section id="privacy" className="section-y scroll-mt-16 border-t border-line">
      <div className="container-page">
        <h2 className="sr-only">Privacy and open source</h2>
        <p ref={ref} className="max-w-[60rem] text-display text-fg">
          {words.map((w, i) => (
            <Word key={i} progress={scrollYProgress} range={[i / words.length, (i + 1) / words.length]}>
              {w}
            </Word>
          ))}
        </p>
        <div className="mt-12 flex flex-col gap-4 text-[15px] sm:flex-row sm:gap-8">
          <TextLink href="/privacy">What we store</TextLink>
          <TextLink href={GITHUB_URL} external>
            Source on GitHub · Apache 2.0
          </TextLink>
        </div>
      </div>
    </section>
  );
}

function Word({
  children,
  progress,
  range,
}: {
  children: string;
  progress: MotionValue<number>;
  range: [number, number];
}) {
  const opacity = useTransform(progress, range, [0.22, 1]);
  return (
    <>
      <motion.span className="motion-reduce:!opacity-100" style={{ opacity }}>
        {children}
      </motion.span>{' '}
    </>
  );
}

'use client';

import { AnimatePresence, motion } from 'motion/react';
import { Mark, EASE_OUT } from './primitives';
import {
  VERDICT_BAR,
  VERDICT_CHIP,
  VERDICT_LABEL,
  type Check,
} from './data';

export type PopupPhase = 'loading' | 'result';

const SCAN_EXTRA = ['reuters.com', 'apnews.com'];

export default function ExtensionPopup({
  check,
  phase,
  className = '',
}: {
  check: Check;
  phase: PopupPhase;
  className?: string;
}) {
  return (
    <div className={`elevated w-full max-w-[360px] rounded-[16px] bg-panel p-4 text-left ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mark pixels={false} className="h-3.5 w-auto" />
          <span className="text-[13px] font-medium text-fg">Truvanta</span>
        </div>
        <span className="font-mono text-[11px] text-fg-3">
          {phase === 'loading' ? 'checking…' : `${check.sources.length} sources`}
        </span>
      </div>

      <p className="mt-3 line-clamp-2 border-l-2 border-line-strong pl-3 text-[13px] leading-[1.45] text-fg-2">
        {check.claim}
      </p>

      <div className="relative mt-4 min-h-[188px]">
        <AnimatePresence mode="wait" initial={false}>
          {phase === 'loading' ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, ease: EASE_OUT }}
            >
              <Scanning domains={[...check.sources.map((s) => s.domain), ...SCAN_EXTRA]} />
            </motion.div>
          ) : (
            <motion.div
              key={`result-${check.verdict}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.22, ease: EASE_OUT }}
            >
              <Result check={check} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function VerdictChip({ check }: { check: Check }) {
  return (
    <span className={`inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-[12px] font-medium tracking-[0.01em] ${VERDICT_CHIP[check.verdict]}`}>
      <span className={`size-1.5 rounded-full ${VERDICT_BAR[check.verdict]}`} />
      {VERDICT_LABEL[check.verdict]}
    </span>
  );
}

function Result({ check }: { check: Check }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <VerdictChip check={check} />
        <span className="font-mono text-[12px] text-fg-2">{check.confidence}% confidence</span>
      </div>
      <div className="mt-3 h-[3px] overflow-hidden rounded-full bg-panel-2">
        <motion.div
          className={`h-full origin-left rounded-full ${VERDICT_BAR[check.verdict]}`}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: check.confidence / 100 }}
          transition={{ duration: 0.5, ease: EASE_OUT, delay: 0.05 }}
        />
      </div>
      <p className="mt-3 text-[13px] leading-[1.5] text-fg-2">{check.summary}</p>
      <ul className="mt-3 flex flex-col gap-1.5">
        {check.sources.map((s, i) => (
          <motion.li
            key={s.domain}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: EASE_OUT, delay: 0.12 + i * 0.06 }}
            className="flex items-center gap-2.5 rounded-[8px] bg-canvas/50 px-2.5 py-2"
          >
            <span className="grid size-5 shrink-0 place-items-center rounded-[5px] bg-panel-2 text-[10px] font-semibold text-fg-2">
              {s.name[0]}
            </span>
            <span className="min-w-0 flex-1 truncate text-[12px] text-fg">{s.name}</span>
            <span className="hidden font-mono text-[11px] text-fg-3 sm:inline">{s.domain}</span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

function Scanning({ domains }: { domains: string[] }) {
  return (
    <div>
      <div className="flex items-center gap-2 text-[12px] text-fg-2">
        <motion.span
          className="size-1.5 rounded-full bg-fg-2"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />
        Searching sources
      </div>
      <ul className="mt-3 flex flex-col gap-1.5">
        {domains.map((d, i) => (
          <motion.li
            key={d}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25, ease: EASE_OUT, delay: i * 0.12 }}
            className="flex items-center justify-between rounded-[8px] bg-canvas/50 px-2.5 py-2"
          >
            <span className="font-mono text-[11px] text-fg-2">{d}</span>
            <motion.span
              className="h-[3px] w-14 overflow-hidden rounded-full bg-panel-2"
              aria-hidden
            >
              <motion.span
                className="block h-full origin-left rounded-full bg-fg-3"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.1 + i * 0.12 }}
              />
            </motion.span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

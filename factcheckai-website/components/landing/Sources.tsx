import { Reveal } from './primitives';

// Publishers whose pages decided verdicts in the evaluation run (October 2026).
const ROW_A = [
  'Snopes', 'PolitiFact', 'AFP Fact Check', 'AP News', 'FactCheck.org', 'Full Fact', 'Africa Check',
  'BOOM', 'Vishvas News', 'FACTLY', 'AAP', 'VOA',
];
const ROW_B = [
  'Wikipedia', 'Britannica', 'BBC', 'NOAA', 'Scientific American', 'Live Science', 'Science Daily',
  'Healthline', 'NPR', 'NDTV', 'The Times of India', 'Universe Today',
];

function Row({ names, reverse = false }: { names: string[]; reverse?: boolean }) {
  // The list is rendered twice so the loop is seamless; the copy is hidden from screen readers.
  return (
    <div className="marquee-mask overflow-hidden">
      <div className={`marquee-track ${reverse ? 'marquee-reverse' : ''}`}>
        {[0, 1].map((copy) => (
          <ul key={copy} aria-hidden={copy === 1} className="flex shrink-0 gap-3 pr-3">
            {names.map((n) => (
              <li
                key={n}
                className="whitespace-nowrap rounded-full bg-panel px-4 py-2 text-[14px] text-fg-2 shadow-[inset_0_0_0_1px_var(--color-line)]"
              >
                {n}
              </li>
            ))}
          </ul>
        ))}
      </div>
    </div>
  );
}

export default function Sources() {
  return (
    <section className="section-y" aria-labelledby="sources-title">
      <div className="container-page">
        <Reveal className="mx-auto max-w-[44rem] text-center">
          <h2 id="sources-title" className="text-display text-fg">
            Where the answers come from.
          </h2>
          <p className="mt-5 text-lead text-fg-2">
            Professional fact-checkers, news wires, reference works and research, searched together
            for every claim. These are publishers whose pages decided verdicts in our evaluation.
          </p>
        </Reveal>
      </div>
      <Reveal delay={0.1} className="mt-14 flex flex-col gap-3">
        <Row names={ROW_A} />
        <Row names={ROW_B} reverse />
      </Reveal>
    </section>
  );
}

export type Verdict = 'true' | 'unsure' | 'false';

export type Source = { name: string; domain: string };

export type Check = {
  claim: string;
  verdict: Verdict;
  confidence: number;
  summary: string;
  sources: Source[];
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  true: 'True',
  unsure: 'Uncertain',
  false: 'False',
};

// Full class strings so Tailwind can see them.
export const VERDICT_TEXT: Record<Verdict, string> = {
  true: 'text-true',
  unsure: 'text-unsure',
  false: 'text-false',
};

export const VERDICT_CHIP: Record<Verdict, string> = {
  true: 'bg-true/12 text-true',
  unsure: 'bg-unsure/12 text-unsure',
  false: 'bg-false/12 text-false',
};

export const VERDICT_BAR: Record<Verdict, string> = {
  true: 'bg-true',
  unsure: 'bg-unsure',
  false: 'bg-false',
};

// Illustrative examples shown in the page's product mockups.
export const CHECKS: Record<Verdict, Check> = {
  true: {
    claim: 'Atmospheric CO₂ has passed 420 ppm at Mauna Loa.',
    verdict: 'true',
    confidence: 97,
    summary:
      'Continuous readings from NOAA and Scripps have stayed above 420 ppm since 2023, and the annual rise continues.',
    sources: [
      { name: 'NOAA Global Monitoring Laboratory', domain: 'gml.noaa.gov' },
      { name: 'Scripps Institution of Oceanography', domain: 'scripps.ucsd.edu' },
    ],
  },
  unsure: {
    claim: 'Drinking coffee every day lowers your risk of type 2 diabetes.',
    verdict: 'unsure',
    confidence: 58,
    summary:
      'Large observational studies link coffee to lower risk, but they can’t show cause and effect. Controlled trials so far are small.',
    sources: [
      { name: 'Harvard T.H. Chan School of Public Health', domain: 'hsph.harvard.edu' },
      { name: 'Cochrane Library', domain: 'cochranelibrary.com' },
    ],
  },
  false: {
    claim: 'The Great Wall of China is visible from the Moon with the naked eye.',
    verdict: 'false',
    confidence: 96,
    summary:
      'Astronauts consistently report it can’t be seen from the Moon. Even from low Earth orbit it is barely visible.',
    sources: [
      { name: 'NASA', domain: 'nasa.gov' },
      { name: 'Scientific American', domain: 'scientificamerican.com' },
    ],
  },
};

export const GITHUB_URL = 'https://github.com/BharatChandra-sys/TruvantaAI';
export const INSTALL_URL = '/install';

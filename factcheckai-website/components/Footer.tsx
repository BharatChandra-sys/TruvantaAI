import Link from 'next/link';
import { Wordmark } from '@/components/landing/primitives';
import { GITHUB_URL, INSTALL_URL } from '@/components/landing/data';

const COLUMNS = [
  {
    title: 'Product',
    links: [
      { href: '/#how-it-works', label: 'How it works' },
      { href: INSTALL_URL, label: 'Install' },
      { href: GITHUB_URL, label: 'GitHub', external: true },
    ],
  },
  {
    title: 'Help',
    links: [
      { href: '/support', label: 'Support' },
      { href: '/#faq', label: 'FAQ' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { href: '/privacy', label: 'Privacy' },
      { href: '/terms', label: 'Terms' },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-line bg-raised">
      <div className="container-page flex flex-col gap-12 py-14 md:flex-row md:justify-between">
        <div className="flex flex-col gap-3">
          <Link href="/" aria-label="Truvanta home" className="self-start rounded-md">
            <Wordmark />
          </Link>
          <p className="max-w-[16rem] text-caption text-fg-3">Fact-checking that shows its sources.</p>
        </div>
        <div className="grid grid-cols-3 gap-10 sm:gap-16">
          {COLUMNS.map((col) => (
            <div key={col.title} className="flex flex-col gap-3">
              <h3 className="text-caption font-medium text-fg">{col.title}</h3>
              {col.links.map((l) => (
                <Link
                  key={l.label}
                  href={l.href}
                  {...('external' in l && l.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                  className="text-caption text-fg-3 transition-colors duration-150 hover:text-fg"
                >
                  {l.label}
                </Link>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="container-page">
        <p className="border-t border-line py-6 text-caption text-fg-3">© {new Date().getFullYear()} Truvanta</p>
      </div>
    </footer>
  );
}

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from 'motion/react';
import { EASE_OUT, EASE_OUT_EXPO, PillLink, Wordmark } from '@/components/landing/primitives';
import { GITHUB_URL, INSTALL_URL } from '@/components/landing/data';

const LINKS = [
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#faq', label: 'FAQ' },
  { href: '/privacy', label: 'Privacy' },
  { href: GITHUB_URL, label: 'GitHub', external: true },
];

export default function Header() {
  const pathname = usePathname();
  const { scrollY } = useScroll();
  const [hidden, setHidden] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  useMotionValueEvent(scrollY, 'change', (y) => {
    const prev = scrollY.getPrevious() ?? 0;
    setScrolled(y > 8);
    setHidden(y > 240 && y > prev);
  });

  // Close the menu on navigation; lock page scroll while it's open.
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setMenuOpen(false);
  }

  useEffect(() => {
    if (!menuOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMenuOpen(false);
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const solid = scrolled || menuOpen;

  return (
    <motion.header
      className="fixed inset-x-0 top-0 z-50"
      animate={{ y: hidden && !menuOpen ? '-100%' : '0%' }}
      transition={{ duration: 0.3, ease: EASE_OUT }}
    >
      <div
        className={`border-b transition-[background-color,border-color] duration-300 ${
          solid
            ? 'border-line bg-canvas/75 backdrop-blur-[20px] backdrop-saturate-[1.8]'
            : 'border-transparent bg-transparent'
        }`}
      >
        <div className="container-page grid h-16 grid-cols-[1fr_auto] items-center md:grid-cols-[1fr_auto_1fr]">
          <Link href="/" aria-label="Truvanta home" className="justify-self-start rounded-md">
            <Wordmark />
          </Link>

          <nav
            aria-label="Main"
            className="hidden items-center md:flex"
            onMouseLeave={() => setHovered(null)}
          >
            {LINKS.map((l) => (
              <Link
                key={l.label}
                href={l.href}
                {...(l.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                aria-current={l.href === pathname ? 'page' : undefined}
                onMouseEnter={() => setHovered(l.label)}
                className={`relative rounded-full px-3.5 py-1.5 text-[13px] transition-colors duration-150 ${
                  l.href === pathname ? 'text-fg' : 'text-fg-2 hover:text-fg'
                }`}
              >
                {hovered === l.label && (
                  <motion.span
                    layoutId="nav-hover"
                    className="absolute inset-0 rounded-full bg-white/[0.06]"
                    transition={{ type: 'spring', visualDuration: 0.3, bounce: 0 }}
                  />
                )}
                <span className="relative">{l.label}</span>
              </Link>
            ))}
          </nav>

          <div className="flex items-center justify-self-end gap-2">
            <span className="hidden sm:block">
              <PillLink href={INSTALL_URL} variant="neutral" size="sm">
                Get extension
              </PillLink>
            </span>
            <button
              type="button"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              aria-controls="mobile-menu"
              onClick={() => setMenuOpen((o) => !o)}
              className="relative -mr-2 grid size-10 place-items-center rounded-full md:hidden"
            >
              <span
                className={`absolute h-[1.5px] w-[18px] rounded-full bg-fg transition-transform duration-300 ease-out ${
                  menuOpen ? 'rotate-45' : '-translate-y-[4px]'
                }`}
              />
              <span
                className={`absolute h-[1.5px] w-[18px] rounded-full bg-fg transition-transform duration-300 ease-out ${
                  menuOpen ? '-rotate-45' : 'translate-y-[4px]'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <motion.div
            id="mobile-menu"
            className="fixed inset-x-0 top-16 bottom-0 bg-canvas md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
          >
            <nav aria-label="Mobile" className="container-page flex flex-col pt-6">
              {[...LINKS, { href: '/support', label: 'Support' }].map((l, i) => (
                <motion.div
                  key={l.label}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: EASE_OUT_EXPO, delay: 0.04 + i * 0.04 }}
                >
                  <Link
                    href={l.href}
                    onClick={() => setMenuOpen(false)}
                    {...('external' in l && l.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                    className="block border-b border-line py-4 text-[26px] font-semibold tracking-[-0.025em] text-fg"
                  >
                    {l.label}
                  </Link>
                </motion.div>
              ))}
              <motion.div
                className="mt-10"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: EASE_OUT_EXPO, delay: 0.26 }}
              >
                <PillLink href={INSTALL_URL} className="w-full">
                  Get the extension, free
                </PillLink>
              </motion.div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

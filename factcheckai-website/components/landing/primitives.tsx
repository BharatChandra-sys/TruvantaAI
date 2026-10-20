'use client';

import Link from 'next/link';
import { motion, type HTMLMotionProps } from 'motion/react';

export const EASE_OUT = [0.23, 1, 0.32, 1] as const;
export const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const;
export const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const;
export const EASE_SHEET = [0.32, 0.72, 0, 1] as const;

/** One entrance per content group, played once. */
export function Reveal({
  y = 16,
  delay = 0,
  amount = 0.3,
  ...props
}: HTMLMotionProps<'div'> & { y?: number; delay?: number; amount?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount }}
      transition={{ duration: 0.9, ease: EASE_OUT_EXPO, delay }}
      {...props}
    />
  );
}

type ButtonProps = {
  href: string;
  children: React.ReactNode;
  variant?: 'accent' | 'neutral';
  size?: 'md' | 'sm';
  className?: string;
};

export function PillLink({ href, children, variant = 'accent', size = 'md', className = '' }: ButtonProps) {
  const tone =
    variant === 'accent'
      ? 'bg-accent text-on-accent hover:bg-accent-hover'
      : 'bg-fg text-canvas hover:bg-white';
  const dims = size === 'md' ? 'h-12 px-6 text-[15px]' : 'h-8 px-3.5 text-[13px]';
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center rounded-full font-medium tracking-[-0.01em] transition-[background-color,transform] duration-150 ease-out active:scale-[0.97] ${tone} ${dims} ${className}`}
    >
      {children}
    </Link>
  );
}

export function TextLink({
  href,
  children,
  external = false,
  className = '',
}: {
  href: string;
  children: React.ReactNode;
  external?: boolean;
  className?: string;
}) {
  return (
    <Link
      href={href}
      {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      className={`group inline-flex items-center gap-1 text-fg-2 transition-colors duration-150 hover:text-fg ${className}`}
    >
      {children}
      <Chevron className="size-3.5 transition-transform duration-200 ease-out group-hover:translate-x-0.5" />
    </Link>
  );
}

export function Chevron({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden className={className}>
      <path d="M6 3.5 10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Flat Truvanta logo: the T with the check woven through it. */
export function Mark({ className = '', pixels = true }: { className?: string; pixels?: boolean }) {
  return (
    <svg viewBox="0 0 40 31" fill="none" aria-hidden className={className}>
      <path d="M11.6 9.6V24.6C11.6 27.5 13.2 29.2 16.2 29.2" stroke="var(--color-fg)" strokeWidth="4" />
      <path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="var(--color-canvas)" strokeWidth="6.6" strokeLinejoin="round" />
      <path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="var(--color-accent)" strokeWidth="4.2" strokeLinejoin="round" />
      <path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H32.4L26 9.2H10.6C6.4 9.2 3 9.9 0.4 11.4Z" fill="var(--color-fg)" />
      <path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H12.4C8.2 3 5.6 5.4 4.4 9.6 2.8 10 1.4 10.6 0.4 11.4Z" fill="var(--color-accent)" />
      {pixels && (
        <g fill="var(--color-accent)">
          <rect x="37.2" y="0.2" width="2.7" height="2.7" rx="0.5" />
          <rect x="34.2" y="3" width="1.9" height="1.9" rx="0.4" />
          <rect x="36.3" y="5.8" width="2.1" height="2.1" rx="0.4" />
          <rect x="34.8" y="10.2" width="2" height="2" rx="0.4" fillOpacity="0.55" />
        </g>
      )}
    </svg>
  );
}

/** Logo plus wordmark, used in the header and footer. */
export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`flex items-center gap-2.5 text-fg ${className}`}>
      <Mark className="h-[22px] w-auto" />
      <span className="text-[16px] font-semibold tracking-[-0.02em]">Truvanta</span>
    </span>
  );
}

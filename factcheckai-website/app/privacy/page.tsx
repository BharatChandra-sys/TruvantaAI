import type { Metadata } from 'next';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'TruvantaAI Privacy Policy - Learn how we protect your data with zero-knowledge fact-checking. GDPR and CCPA compliant.',
  alternates: {
    canonical: 'https://truvantaai.tech/privacy',
  },
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <Header />
      
      <main className="w-full pt-24 pb-12 bg-surface max-w-4xl mx-auto px-4 md:px-8 flex-1">
        <div className="flex flex-col gap-8">
          {/* Header */}
          <div className="flex flex-col gap-4">
            <h1 className="text-5xl font-bold text-on-surface">Privacy Policy</h1>
            <p className="text-lg text-on-surface-variant">
              Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>

          {/* Introduction */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">Our Commitment to Privacy</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TruvantaAI is built on the principle of zero-knowledge fact-checking. We believe privacy is a fundamental right, not a premium feature. This policy explains what data we collect (spoiler: almost nothing), how we use it, and your rights under GDPR, CCPA, and other privacy regulations.
            </p>
          </section>

          {/* What We Collect */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">1. Data Collection</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">1.1 Extension Usage</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              When you use the TruvantaAI browser extension:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li><strong>Claim Text:</strong> The text you select for fact-checking is sent to our backend for analysis. We do NOT log or store this text.</li>
              <li><strong>Anonymous Session IDs:</strong> A temporary, randomly-generated session identifier is used to group related checks within a browsing session. This ID cannot be linked to your identity and is discarded after 24 hours.</li>
              <li><strong>No Browsing History:</strong> We never collect URLs, page titles, or browsing patterns.</li>
              <li><strong>No User Accounts:</strong> The extension operates anonymously. We don't require registration or authentication for core features.</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">1.2 Website Analytics</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              This website uses privacy-respecting analytics to understand aggregate usage:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Page views and navigation patterns (aggregated, no personal tracking)</li>
              <li>Referrer sources (e.g., search engines, social media)</li>
              <li>Device type and browser version (for compatibility testing)</li>
              <li>We use <strong>Plausible Analytics</strong>, a GDPR-compliant, cookie-free analytics provider</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">1.3 What We DON'T Collect</h3>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>IP addresses (anonymized immediately)</li>
              <li>Email addresses or contact information (unless you voluntarily submit feedback)</li>
              <li>Cookies or persistent identifiers</li>
              <li>Cross-site tracking or third-party advertising data</li>
              <li>Sensitive personal information (race, religion, political views, health data)</li>
            </ul>
          </section>

          {/* How We Use Data */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">2. Data Usage</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              The minimal data we process is used exclusively for:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li><strong>Fact-Checking Analysis:</strong> Submitted claims are analyzed by our ML models and evidence retrieval systems to generate verdicts.</li>
              <li><strong>Service Improvement:</strong> Aggregate, anonymous usage statistics help us optimize model performance and identify bugs.</li>
              <li><strong>Research:</strong> De-identified, aggregated data may inform academic publications on misinformation detection (never individual claims).</li>
            </ul>
            <p className="text-base text-on-surface-variant leading-relaxed mt-4">
              <strong>We NEVER:</strong> Sell data, share data with advertisers, or use data for behavioral profiling or targeted advertising.
            </p>
          </section>

          {/* Data Storage & Security */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">3. Data Storage & Security</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">3.1 Where Data is Stored</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Our backend infrastructure is hosted on <strong>Render.com</strong> (US-based servers). Claims are processed in-memory and NOT persisted to disk or databases. Session IDs are stored temporarily in Redis with a 24-hour TTL.
            </p>

            <h3 className="text-xl font-semibold text-on-surface mt-6">3.2 Security Measures</h3>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>All data transmission uses <strong>TLS 1.3 encryption</strong></li>
              <li>Backend APIs are protected by rate limiting and CORS policies</li>
              <li>No persistent storage of user-submitted content</li>
              <li>Regular security audits and dependency vulnerability scans</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">3.3 Data Retention</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Since we don't log claims or personal data, there's nothing to retain. Temporary session IDs expire after 24 hours. Aggregate analytics are retained indefinitely for research purposes (fully anonymized).
            </p>
          </section>

          {/* Third-Party Services */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">4. Third-Party Services</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              We use the following third-party services:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li><strong>Render.com:</strong> Infrastructure hosting (Privacy Policy: <a href="https://render.com/privacy" target="_blank" className="text-surface-tint hover:underline">render.com/privacy</a>)</li>
              <li><strong>Plausible Analytics:</strong> Privacy-first website analytics (Privacy Policy: <a href="https://plausible.io/privacy" target="_blank" className="text-surface-tint hover:underline">plausible.io/privacy</a>)</li>
              <li><strong>GitHub:</strong> Open-source code hosting (no user data shared)</li>
            </ul>
            <p className="text-base text-on-surface-variant leading-relaxed mt-4">
              We do NOT use Google Analytics, Facebook Pixel, or any advertising/tracking networks.
            </p>
          </section>

          {/* Your Rights (GDPR/CCPA) */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">5. Your Rights</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">5.1 GDPR Rights (EU Users)</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Under the General Data Protection Regulation (GDPR), you have the right to:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li><strong>Access:</strong> Request a copy of any personal data we hold (we hold none)</li>
              <li><strong>Rectification:</strong> Correct inaccurate data (not applicable—we don't store personal data)</li>
              <li><strong>Erasure:</strong> Request deletion of your data (automatic after 24 hours for session IDs)</li>
              <li><strong>Data Portability:</strong> Receive your data in a machine-readable format (not applicable)</li>
              <li><strong>Objection:</strong> Object to data processing (you can stop using the service at any time)</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">5.2 CCPA Rights (California Users)</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Under the California Consumer Privacy Act (CCPA), you have the right to:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Know what personal information is collected</li>
              <li>Request deletion of personal information</li>
              <li>Opt-out of the "sale" of personal information (we never sell data)</li>
              <li>Non-discrimination for exercising your rights</li>
            </ul>

            <p className="text-base text-on-surface-variant leading-relaxed mt-4">
              To exercise any rights, contact us at: <a href="mailto:contact@truvantaai.tech" className="text-surface-tint hover:underline">contact@truvantaai.tech</a>
            </p>
          </section>

          {/* Cookies */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">6. Cookies & Local Storage</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              <strong>We do NOT use cookies.</strong> The extension may use browser local storage to save user preferences (theme settings, filter options) locally on your device. This data never leaves your browser.
            </p>
          </section>

          {/* Children's Privacy */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">7. Children's Privacy</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TruvantaAI does not knowingly collect data from children under 13. If you believe we've inadvertently collected such data, contact us immediately at <a href="mailto:contact@truvantaai.tech" className="text-surface-tint hover:underline">contact@truvantaai.tech</a>.
            </p>
          </section>

          {/* International Transfers */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">8. International Data Transfers</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Our servers are located in the United States. If you access TruvantaAI from outside the US, your data may be transferred to US servers. We comply with EU-US Privacy Shield principles (where applicable) and implement appropriate safeguards.
            </p>
          </section>

          {/* Changes to Policy */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">9. Changes to This Policy</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              We may update this policy to reflect changes in our practices or legal requirements. Material changes will be announced via:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>A notice on this website</li>
              <li>A notification in the browser extension (if installed)</li>
              <li>GitHub repository announcements</li>
            </ul>
          </section>

          {/* Contact */}
          <section className="flex flex-col gap-4 bg-surface-container p-6 rounded-xl">
            <h2 className="text-3xl font-bold text-on-surface">10. Contact Us</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              For privacy inquiries, data requests, or security concerns:
            </p>
            <ul className="list-none text-base text-on-surface-variant leading-relaxed space-y-2">
              <li><strong>Email:</strong> <a href="mailto:contact@truvantaai.tech" className="text-surface-tint hover:underline">contact@truvantaai.tech</a></li>
              <li><strong>Website:</strong> <a href="https://gari.live" target="_blank" className="text-surface-tint hover:underline">gari.live</a></li>
            </ul>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}

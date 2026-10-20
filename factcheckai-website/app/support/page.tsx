import type { Metadata } from 'next';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import MaterialSymbols from '@/components/MaterialSymbols';

export const metadata: Metadata = {
  title: 'Support & Contact',
  description: 'Get help with TruvantaAI, report issues, or contribute to the project. Contact our support team.',
  alternates: {
    canonical: 'https://truvantaai.tech/support',
  },
};

export default function Support() {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <MaterialSymbols />
      <Header />
      
      <main className="w-full pt-24 pb-12 bg-surface max-w-4xl mx-auto px-4 md:px-8 flex-1">
        <div className="flex flex-col gap-8">
          {/* Header */}
          <div className="flex flex-col gap-4">
            <h1 className="text-5xl font-bold text-on-surface">Support & Contact</h1>
            <p className="text-lg text-on-surface-variant">
              Get help, report issues, or contribute to the project.
            </p>
          </div>

          {/* Quick Links */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <a
              href="mailto:contact@gari.live?subject=Bug%20Report"
              className="bg-surface-container p-6 rounded-xl flex flex-col gap-3 hover:bg-surface-container-high transition-colors"
            >
              <span className="material-symbols-outlined text-3xl text-error">bug_report</span>
              <h3 className="text-xl font-semibold text-on-surface">Report a Bug</h3>
              <p className="text-sm text-on-surface-variant">
                Found an issue? Email us with detailed reproduction steps.
              </p>
            </a>

            <a
              href="mailto:contact@gari.live?subject=Feature%20Request"
              className="bg-surface-container p-6 rounded-xl flex flex-col gap-3 hover:bg-surface-container-high transition-colors"
            >
              <span className="material-symbols-outlined text-3xl text-surface-tint">lightbulb</span>
              <h3 className="text-xl font-semibold text-on-surface">Feature Request</h3>
              <p className="text-sm text-on-surface-variant">
                Have an idea? Share your feature suggestions with us.
              </p>
            </a>

            <a
              href="mailto:contact@gari.live?subject=General%20Inquiry"
              className="bg-surface-container p-6 rounded-xl flex flex-col gap-3 hover:bg-surface-container-high transition-colors"
            >
              <span className="material-symbols-outlined text-3xl text-secondary">mail</span>
              <h3 className="text-xl font-semibold text-on-surface">General Support</h3>
              <p className="text-sm text-on-surface-variant">
                Have questions? We're here to help with any inquiries.
              </p>
            </a>
          </div>

          {/* FAQ */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">Frequently Asked Questions</h2>
            
            <div className="bg-surface-container p-6 rounded-xl flex flex-col gap-4">
              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-2">How do I install the extension?</h3>
                <p className="text-base text-on-surface-variant leading-relaxed">
                  Visit the <a href="https://chrome.google.com/webstore" target="_blank" className="text-surface-tint hover:underline">Chrome Web Store</a> or <a href="https://microsoftedge.microsoft.com/addons" target="_blank" className="text-surface-tint hover:underline">Microsoft Edge Add-ons</a> and search for "TruvantaAI". Click "Add" to install.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-2">Why is a verdict marked "UNCERTAIN"?</h3>
                <p className="text-base text-on-surface-variant leading-relaxed">
                  UNCERTAIN verdicts indicate conflicting evidence, insufficient authoritative sources, or emerging topics without clear consensus. This reflects honest epistemic limitations rather than a failure of the system.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-2">Can I use TruvantaAI offline?</h3>
                <p className="text-base text-on-surface-variant leading-relaxed">
                  No. Fact-checking requires querying our backend evidence database and ML models. A network connection is required.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-2">How can I report a bug or suggest features?</h3>
                <p className="text-base text-on-surface-variant leading-relaxed">
                  Email us at <a href="mailto:contact@gari.live" className="text-surface-tint hover:underline">contact@gari.live</a> with details about the issue or your feature request.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-on-surface mb-2">Is TruvantaAI free?</h3>
                <p className="text-base text-on-surface-variant leading-relaxed">
                  Yes, completely free. No subscriptions, no premium tiers, no ads.
                </p>
              </div>
            </div>
          </section>

          {/* Contact Methods */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">Contact Methods</h2>

            <div className="bg-surface-container-low p-6 rounded-xl">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-surface-tint">mail</span>
                    <h3 className="text-lg font-semibold text-on-surface">Email Support</h3>
                  </div>
                  <p className="text-sm text-on-surface-variant">All inquiries:</p>
                  <a href="mailto:contact@gari.live" className="text-base text-surface-tint hover:underline">
                    contact@gari.live
                  </a>
                  <p className="text-sm text-on-surface-variant mt-4">Website:</p>
                  <a href="https://gari.live" target="_blank" className="text-base text-surface-tint hover:underline">
                    gari.live
                  </a>
                </div>

                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-secondary">schedule</span>
                    <h3 className="text-lg font-semibold text-on-surface">Response Time</h3>
                  </div>
                  <p className="text-sm text-on-surface-variant">
                    We typically respond to all inquiries within 24-48 hours during business days.
                  </p>
                  <p className="text-sm text-on-surface-variant mt-4">
                    For urgent security issues, please mark your email subject with <strong>[SECURITY]</strong> for priority handling.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Security Disclosures */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">Security Vulnerability Disclosure</h2>
            <div className="bg-error-container/10 border border-error/30 p-6 rounded-xl">
              <p className="text-base text-on-surface leading-relaxed mb-4">
                If you discover a security vulnerability, please email us with <strong>[SECURITY]</strong> in the subject line:
              </p>
              <a href="mailto:contact@gari.live" className="text-lg text-error hover:underline font-semibold">
                contact@gari.live
              </a>
              <p className="text-sm text-on-surface-variant mt-4">
                We aim to respond within 48 hours and will credit responsible disclosures in our changelog.
              </p>
            </div>
          </section>

          {/* Response Times */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">Expected Response Times</h2>
            <div className="bg-surface-container p-6 rounded-xl">
              <ul className="space-y-3 text-base text-on-surface-variant">
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-error shrink-0">priority_high</span>
                  <div>
                    <strong className="text-on-surface">Security Issues:</strong> 48 hours
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-tertiary shrink-0">bug_report</span>
                  <div>
                    <strong className="text-on-surface">Bug Reports:</strong> 3-5 business days
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-surface-tint shrink-0">help</span>
                  <div>
                    <strong className="text-on-surface">General Inquiries:</strong> 1 week
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-secondary shrink-0">lightbulb</span>
                  <div>
                    <strong className="text-on-surface">Feature Requests:</strong> Discussed in community forums
                  </div>
                </li>
              </ul>
            </div>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}

import type { Metadata } from 'next';
import Header from '@/components/Header';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'TruvantaAI Terms of Service - Review our terms and conditions for using the browser extension.',
  alternates: {
    canonical: 'https://truvantaai.tech/terms',
  },
};

export default function TermsOfService() {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <Header />
      
      <main className="w-full pt-24 pb-12 bg-surface max-w-4xl mx-auto px-4 md:px-8 flex-1">
        <div className="flex flex-col gap-8">
          {/* Header */}
          <div className="flex flex-col gap-4">
            <h1 className="text-5xl font-bold text-on-surface">Terms of Service</h1>
            <p className="text-lg text-on-surface-variant">
              Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>

          {/* Introduction */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">1. Acceptance of Terms</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              By installing or using TruvantaAI ("the Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.
            </p>
          </section>

          {/* Service Description */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">2. Service Description</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TruvantaAI is an open-source browser extension that uses machine learning and evidence retrieval to assess the credibility of user-submitted claims. The Service provides:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Automated fact-checking analysis using ML models</li>
              <li>Evidence retrieval from peer-reviewed sources</li>
              <li>Calibrated confidence scores and uncertainty estimates</li>
              <li>Citation links to source materials</li>
            </ul>
          </section>

          {/* User Responsibilities */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">3. User Responsibilities</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">3.1 Appropriate Use</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">You agree to use TruvantaAI only for lawful purposes. You will NOT:</p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Submit malicious content, spam, or abusive material</li>
              <li>Attempt to reverse-engineer, decompile, or extract proprietary models</li>
              <li>Use automated tools to overload our backend infrastructure</li>
              <li>Circumvent rate limits or security measures</li>
              <li>Impersonate other users or entities</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">3.2 Critical Decisions</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TruvantaAI is a research tool designed to assist critical thinking—NOT replace it. You acknowledge that:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>AI models can make errors, especially on emerging or niche topics</li>
              <li>Verdicts should be considered alongside original sources</li>
              <li>The Service is NOT suitable for life-critical decisions (medical, legal, financial advice)</li>
            </ul>
          </section>

          {/* Intellectual Property */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">4. Intellectual Property</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">4.1 Open-Source License</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TruvantaAI's source code is licensed under the <strong>MIT License</strong>. You are free to use, modify, and distribute the code subject to the license terms: <a href="https://opensource.org/licenses/MIT" target="_blank" className="text-surface-tint hover:underline">opensource.org/licenses/MIT</a>
            </p>

            <h3 className="text-xl font-semibold text-on-surface mt-6">4.2 User-Submitted Content</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Claims you submit for fact-checking are processed transiently and NOT stored. You retain all rights to your submissions. By using the Service, you grant us a temporary, non-exclusive license to process your submissions solely for generating verdicts.
            </p>

            <h3 className="text-xl font-semibold text-on-surface mt-6">4.3 Trademarks</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              "TruvantaAI," our logo, and branding are trademarks. You may NOT use these marks without prior written permission, except as required to identify the software in compliance with the MIT License.
            </p>
          </section>

          {/* Disclaimers */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">5. Disclaimers & Limitations</h2>
            
            <h3 className="text-xl font-semibold text-on-surface mt-4">5.1 No Warranty</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. We do not guarantee:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Accuracy, completeness, or reliability of verdicts</li>
              <li>Uninterrupted or error-free operation</li>
              <li>That our models are free from bias or errors</li>
            </ul>

            <h3 className="text-xl font-semibold text-on-surface mt-6">5.2 Limitation of Liability</h3>
            <p className="text-base text-on-surface-variant leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, TruvantaAI and its contributors SHALL NOT BE LIABLE for:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Indirect, incidental, or consequential damages</li>
              <li>Loss of data, profits, or business opportunities</li>
              <li>Damages arising from reliance on automated verdicts</li>
            </ul>
            <p className="text-base text-on-surface-variant leading-relaxed mt-4">
              Your sole remedy is to stop using the Service.
            </p>
          </section>

          {/* Privacy */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">6. Privacy</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              Our data practices are governed by our <a href="/privacy" className="text-surface-tint hover:underline">Privacy Policy</a>. By using the Service, you consent to our minimal data collection as described therein.
            </p>
          </section>

          {/* Modifications */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">7. Modifications to Service</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              We reserve the right to:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Modify or discontinue features without notice</li>
              <li>Impose usage limits or rate limits</li>
              <li>Update models, algorithms, or data sources</li>
            </ul>
            <p className="text-base text-on-surface-variant leading-relaxed mt-4">
              Material changes will be announced via GitHub and in-extension notifications.
            </p>
          </section>

          {/* Termination */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">8. Termination</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              You may stop using the Service at any time by uninstalling the extension. We reserve the right to suspend or terminate access for violations of these Terms, including:
            </p>
            <ul className="list-disc list-inside text-base text-on-surface-variant leading-relaxed space-y-2 ml-4">
              <li>Abusive or malicious use</li>
              <li>Attempts to disrupt service availability</li>
              <li>Violation of applicable laws</li>
            </ul>
          </section>

          {/* Governing Law */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">9. Governing Law</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              These Terms are governed by the laws of [Your Jurisdiction], without regard to conflict of law principles. Disputes shall be resolved in the courts of [Your Jurisdiction].
            </p>
          </section>

          {/* Severability */}
          <section className="flex flex-col gap-4">
            <h2 className="text-3xl font-bold text-on-surface">10. Severability</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              If any provision of these Terms is found unenforceable, the remaining provisions shall remain in full force and effect.
            </p>
          </section>

          {/* Contact */}
          <section className="flex flex-col gap-4 bg-surface-container p-6 rounded-xl">
            <h2 className="text-3xl font-bold text-on-surface">11. Contact</h2>
            <p className="text-base text-on-surface-variant leading-relaxed">
              For questions about these Terms:
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

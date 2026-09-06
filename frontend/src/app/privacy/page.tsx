import Link from "next/link";
import { Card } from "@/components/ui/Card";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-slate-50 px-6 py-12">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="mb-6 inline-block text-sm text-brand-600 underline">
          ← Back to FinanceAI
        </Link>

        <Card>
          <div className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
            <strong>Draft template — not legal advice.</strong> This is a standard starting-point Privacy
            Policy for an early-stage SaaS product, generated to give this app a real policy page rather
            than none at all. Have a lawyer review it against your actual data practices and applicable
            law (e.g. GDPR, CCPA) before relying on it with real customers.
          </div>

          <h1 className="mb-1 text-2xl font-semibold">Privacy Policy</h1>
          <p className="mb-6 text-sm text-slate-500">Last updated: {new Date().toLocaleDateString("en-US")}</p>

          <div className="space-y-6 text-sm leading-relaxed text-slate-700">
            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">1. Information we collect</h2>
              <ul className="list-inside list-disc space-y-1">
                <li>
                  <span className="font-medium">Account information</span>: name, email address, and
                  hashed password when you register.
                </li>
                <li>
                  <span className="font-medium">Business data</span>: whatever you enter or upload —
                  sales, expenses, purchases, inventory, customer/vendor records, and similar.
                </li>
                <li>
                  <span className="font-medium">Usage data</span>: basic request logs (e.g. IP address,
                  timestamps) for security and reliability.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">2. How we use it</h2>
              <p>
                To operate the Service (store and display your business data, compute dashboards and
                reports), to authenticate you and secure your account, to process payments for paid plans,
                to send transactional messages you request (email/WhatsApp report delivery, password
                resets), and to improve reliability and detect abuse.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">3. Third-party service providers</h2>
              <p className="mb-2">
                We share data with the following providers only as needed to deliver the features you use
                — never for advertising or resale:
              </p>
              <ul className="list-inside list-disc space-y-1">
                <li>
                  <span className="font-medium">Stripe</span> — payment processing for paid subscription
                  plans. We never see or store your full card details.
                </li>
                <li>
                  <span className="font-medium">Resend</span> — outbound transactional email (verification
                  links, password resets, report delivery).
                </li>
                <li>
                  <span className="font-medium">Twilio</span> — outbound WhatsApp report delivery, if you
                  use that feature.
                </li>
                <li>
                  <span className="font-medium">Anthropic</span> — powers the AI Assistant, Insights,
                  Forecasting, and Receipt Scanner features. Relevant business data is sent to Anthropic&apos;s
                  API only when you actively use one of these features.
                </li>
                <li>
                  <span className="font-medium">Render and Vercel</span> — cloud hosting for our backend
                  and frontend.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">4. Data retention</h2>
              <p>
                We retain your data for as long as your account is active. If you delete your account, we
                delete or anonymize your data within a reasonable period, except where we&apos;re required
                to keep records longer (e.g. billing records for tax/accounting purposes).
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">5. Security</h2>
              <p>
                We use industry-standard measures (encrypted connections, hashed passwords, access
                controls) to protect your data, but no system is 100% secure — we can&apos;t guarantee
                absolute security.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">6. Your rights</h2>
              <p>
                Depending on your location, you may have rights to access, correct, export, or delete your
                personal data. Contact us to exercise these rights, and we&apos;ll respond within a
                reasonable timeframe.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">7. Cookies and local storage</h2>
              <p>
                We use browser storage to keep you signed in and remember basic preferences. We don&apos;t
                use third-party advertising or tracking cookies.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">8. Children&apos;s privacy</h2>
              <p>The Service is intended for business use by adults and is not directed at children.</p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">9. Changes to this policy</h2>
              <p>
                We may update this Privacy Policy from time to time. Material changes will be reflected by
                updating the &quot;Last updated&quot; date above.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">10. Contact</h2>
              <p>
                Questions about this policy, or requests regarding your data, can be sent to the contact
                address for this business. See also our{" "}
                <Link href="/terms" className="text-brand-600 underline">
                  Terms of Service
                </Link>
                .
              </p>
            </section>
          </div>
        </Card>
      </div>
    </div>
  );
}

import Link from "next/link";
import { Card } from "@/components/ui/Card";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-50 px-6 py-12">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="mb-6 inline-block text-sm text-brand-600 underline">
          ← Back to FinanceAI
        </Link>

        <Card>
          <div className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
            <strong>Draft template — not legal advice.</strong> This is a standard starting-point Terms of
            Service for an early-stage SaaS product, generated to give this app a real policy page rather
            than none at all. Have a lawyer review and adapt it to your actual business, jurisdiction, and
            plans before relying on it with real customers.
          </div>

          <h1 className="mb-1 text-2xl font-semibold">Terms of Service</h1>
          <p className="mb-6 text-sm text-slate-500">Last updated: {new Date().toLocaleDateString("en-US")}</p>

          <div className="space-y-6 text-sm leading-relaxed text-slate-700">
            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">1. Acceptance of terms</h2>
              <p>
                By creating an account or using FinanceAI (&quot;the Service&quot;), you agree to these
                Terms of Service. If you don&apos;t agree, don&apos;t use the Service.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">2. Description of service</h2>
              <p>
                FinanceAI is a business finance management tool covering sales, expenses, purchases,
                inventory, customers, vendors, payments, reporting, and AI-assisted insights. It is a
                record-keeping and analysis aid, not a substitute for a qualified accountant, bookkeeper,
                or tax advisor.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">3. Accounts</h2>
              <p>
                You&apos;re responsible for keeping your login credentials confidential and for all
                activity under your account. You must provide accurate information when registering.
                One account may manage multiple businesses; each business&apos;s data is only visible to
                its own members.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">4. Acceptable use</h2>
              <p>
                You agree not to use the Service to store or process unlawful content, attempt to breach
                its security, resell access without authorization, or use it in a way that could disrupt
                the Service for other users.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">5. Subscriptions and billing</h2>
              <p>
                Some plans are paid subscriptions billed on a recurring basis through our payment
                processor (Stripe). Upgrading, downgrading, and cancellation are handled through the
                Billing settings in-app. Fees are non-refundable except where required by law.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">6. Your data</h2>
              <p>
                You retain ownership of the business data you enter or upload. You&apos;re responsible for
                the accuracy of that data and for having the right to store it. See our{" "}
                <Link href="/privacy" className="text-brand-600 underline">
                  Privacy Policy
                </Link>{" "}
                for how we handle it.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">7. AI features</h2>
              <p>
                The AI Assistant, Insights, Forecasting, and Receipt Scanner features use a third-party AI
                provider (Groq or Anthropic) and generate outputs that may be incomplete or inaccurate.
                Always verify AI-generated financial figures before relying on them for real decisions.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">8. Disclaimers</h2>
              <p>
                The Service is provided &quot;as is&quot; without warranties of any kind, express or
                implied, including fitness for a particular purpose or non-infringement. We don&apos;t
                guarantee the Service will be uninterrupted, error-free, or secure at all times.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">9. Limitation of liability</h2>
              <p>
                To the fullest extent permitted by law, we are not liable for indirect, incidental, or
                consequential damages arising from your use of the Service, including business losses
                resulting from reliance on data or AI outputs generated by it.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">10. Termination</h2>
              <p>
                You may stop using the Service and delete your account at any time. We may suspend or
                terminate accounts that violate these Terms.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">11. Changes to these terms</h2>
              <p>
                We may update these Terms from time to time. Continued use of the Service after an update
                constitutes acceptance of the revised Terms.
              </p>
            </section>

            <section>
              <h2 className="mb-2 text-base font-semibold text-slate-900">12. Contact</h2>
              <p>Questions about these Terms can be sent to the contact address for this business.</p>
            </section>
          </div>
        </Card>
      </div>
    </div>
  );
}

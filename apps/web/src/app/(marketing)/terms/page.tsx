import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-display text-4xl font-semibold">Terms of Service</h1>
      <p className="mt-2 text-sm text-stone-500">Last updated: November 2026</p>

      <div className="mt-8 space-y-6 text-stone-700 leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-ink">1. Using Móyee</h2>
          <p className="mt-2">
            Móyee provides an AI-assisted research workspace for students, postgraduate researchers,
            and professionals. You must keep your account credentials secure and are responsible for
            all activity under your account.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">2. Academic Integrity &amp; Human Responsibility</h2>
          <p className="mt-2">
            Móyee is a research and writing aid, not a substitute for your own academic judgement.
            Although Móyee grounds responses in your sources and validates citations, AI outputs may
            contain errors or omissions. You are solely responsible for verifying every claim,
            citation, and methodology before submitting academic or professional work, and for
            complying with your institution’s policies on AI use.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">3. Your Content &amp; Copyright</h2>
          <p className="mt-2">
            You retain ownership of the notes, matrices, and documents you write in Móyee. By
            uploading files, you confirm that you have the right to store and process them for your
            personal research use. Móyee does not redistribute uploaded full-text documents to other
            users.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">4. Plans, Quotas &amp; Billing</h2>
          <p className="mt-2">
            Free and Pro plans include usage quotas enforced by the platform. Paid subscriptions
            renew automatically at the end of each billing cycle unless cancelled. You may cancel at
            any time from your Account Settings; your Pro access remains active until the end of the
            current period.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">5. Acceptable Use</h2>
          <p className="mt-2">
            You agree not to attempt to bypass plan quotas or access controls, probe or disrupt the
            service, upload malicious files, or use Móyee to fabricate academic evidence.
          </p>
        </section>
      </div>
    </article>
  );
}

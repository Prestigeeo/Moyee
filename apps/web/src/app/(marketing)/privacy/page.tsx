import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-display text-4xl font-semibold">Privacy Policy</h1>
      <p className="mt-2 text-sm text-stone-500">Last updated: November 2026</p>

      <div className="mt-8 space-y-6 text-stone-700 leading-relaxed">
        <section>
          <h2 className="text-lg font-semibold text-ink">1. Information We Collect</h2>
          <p className="mt-2">
            When you create a Móyee account, we collect your email address, name (if provided),
            research preferences, and authentication credentials. Within your workspace, we store
            the research projects, uploaded documents, saved academic metadata, notes, literature
            matrices, writing drafts, and assistant conversations you create.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">2. How We Use Your Information</h2>
          <p className="mt-2">
            We use your information to provide, secure, and improve the Móyee research workspace—including
            processing your uploaded documents, retrieving relevant passages for your research
            questions, enforcing subscription quotas, and sending essential account or billing
            notifications.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">3. AI Processing &amp; Third-Party Providers</h2>
          <p className="mt-2">
            To generate summaries, literature extractions, and grounded answers, Móyee sends relevant
            project context and document excerpts to configured third-party AI model providers (such
            as Google Gemini and Groq). When operating on free-tier provider APIs during initial
            preview phases, submitted prompts and excerpts may be subject to the provider’s standard
            data-retention and service-improvement terms. Do not upload confidential, classified, or
            personally identifiable human-subjects data unless your institutional ethics approval and
            plan tier permit external cloud processing.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">4. Data Isolation &amp; Security</h2>
          <p className="mt-2">
            Your research projects and uploaded files are private to your account. Every request is
            authorised on the server and isolated per user. Uploaded files are stored in private
            object storage and accessed via short-lived signed links.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">5. Your Control, Export &amp; Deletion</h2>
          <p className="mt-2">
            You can edit, export, or delete your projects and documents at any time. You may delete
            your entire account from the Account Settings page, which permanently removes your
            profile, projects, conversations, and usage records from our application database.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">6. Contact</h2>
          <p className="mt-2">
            Questions about privacy can be sent to{" "}
            <a href="mailto:privacy@moyee.app" className="text-brand-600 underline">
              privacy@moyee.app
            </a>
            .
          </p>
        </section>
      </div>
    </article>
  );
}

import Link from "next/link";
import { BookOpenText, FileSearch, Layers, PenLine, Quote, ShieldCheck } from "lucide-react";
import { RotatingTagline } from "@/components/brand/rotating-tagline";
import { buttonClass, Card } from "@/components/ui";
import { BRAND_NAME } from "@/config/brand";

const features = [
  {
    icon: FileSearch,
    title: "Find & understand",
    body: "Search millions of scholarly works, save what matters, and upload your PDFs. Get structured summaries of aims, methods, findings and limitations.",
  },
  {
    icon: Layers,
    title: "Synthesise with evidence",
    body: "Compare studies side by side in an editable literature matrix. Every extracted cell links back to the page it came from.",
  },
  {
    icon: PenLine,
    title: "Write & cite",
    body: "Draft chapters from thesis, article or report templates. Insert citations in APA 7, Harvard or IEEE and export to Word.",
  },
];

const steps = [
  { n: 1, title: "Create a project", body: "Describe your topic, level and research questions." },
  { n: 2, title: "Gather sources", body: "Search the scholarly record or upload papers you already have." },
  { n: 3, title: "Ask and compare", body: "Get answers grounded in your sources, with page-level citations." },
  { n: 4, title: "Write and export", body: "Turn evidence into structured, referenced writing." },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-20 text-center md:pt-28">
        <h1 className="font-display text-6xl font-semibold tracking-tight text-brand-700 md:text-8xl">
          {BRAND_NAME}
        </h1>
        <RotatingTagline className="mt-5 font-display text-2xl text-stone-700 md:text-3xl" />
        <p className="mx-auto mt-6 max-w-2xl text-lg text-stone-600">
          The research workspace where every AI answer traces back to a source. Discover papers,
          understand them, synthesise the literature and write with citations you can trust.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link href="/sign-up" className={buttonClass("primary", "lg")}>Start free</Link>
          <Link href="#how-it-works" className={buttonClass("secondary", "lg")}>See how it works</Link>
        </div>

        {/* Evidence demo */}
        <Card className="mx-auto mt-16 max-w-3xl p-6 text-left">
          <p className="text-sm font-medium text-stone-500">You asked</p>
          <p className="mt-1 text-ink">What methods did the studies use to measure rainfall variability?</p>
          <div className="mt-5 border-t border-stone-100 pt-5">
            <p className="text-sm font-medium text-stone-500">Móyee</p>
            <p className="mt-1 font-reading text-[17px] leading-relaxed text-ink">
              Most studies relied on station-based precipitation records aggregated to seasonal totals
              <Cite n={1} />, while two used satellite-derived estimates to cover areas without stations
              <Cite n={2} />.
            </p>
            <div className="mt-4 rounded-lg border border-brand-100 bg-brand-50 p-4 text-sm">
              <p className="mb-2 flex items-center gap-1.5 font-medium text-brand-800">
                <ShieldCheck className="size-4" aria-hidden /> From your sources
              </p>
              <ol className="space-y-1.5 text-stone-700">
                <li><span className="font-medium">[1]</span> Okafor &amp; Bello (2021), p. 6: “…monthly station records were summed to seasonal totals…”</li>
                <li><span className="font-medium">[2]</span> Mensah et al. (2023), p. 4: “…CHIRPS satellite estimates were used where gauges were absent…”</li>
              </ol>
            </div>
          </div>
        </Card>
      </section>

      {/* Features */}
      <section id="features" className="border-y border-stone-200 bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-3xl font-semibold text-ink md:text-4xl">
            One workspace for the whole research journey
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map(({ icon: Icon, title, body }) => (
              <div key={title}>
                <div className="flex size-11 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <Icon className="size-5" aria-hidden />
                </div>
                <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-stone-600">{body}</p>
              </div>
            ))}
          </div>
          <div className="mt-14 grid gap-6 rounded-xl bg-canvas p-6 md:grid-cols-2">
            <div className="flex gap-3">
              <Quote className="mt-1 size-5 shrink-0 text-accent-600" aria-hidden />
              <p className="text-stone-700">
                <strong>No invented citations.</strong> If your sources don’t support an answer, Móyee says so instead of guessing.
              </p>
            </div>
            <div className="flex gap-3">
              <BookOpenText className="mt-1 size-5 shrink-0 text-accent-600" aria-hidden />
              <p className="text-stone-700">
                <strong>Built for students, researchers and professionals</strong>, from final-year projects to research reports.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="font-display text-3xl font-semibold md:text-4xl">How it works</h2>
          <ol className="mt-12 grid gap-6 md:grid-cols-4">
            {steps.map((s) => (
              <li key={s.n} className="rounded-xl border border-stone-200 bg-white p-5">
                <span className="flex size-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
                  {s.n}
                </span>
                <h3 className="mt-4 font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm text-stone-600">{s.body}</p>
              </li>
            ))}
          </ol>
          <div className="mt-16 rounded-2xl bg-brand-700 px-8 py-12 text-center text-white">
            <h2 className="font-display text-3xl font-semibold">Start your research with clarity</h2>
            <p className="mt-3 text-brand-100">Free to start. Pro is US$10/month when you need more.</p>
            <Link href="/sign-up" className={buttonClass("secondary", "lg", "mt-8 border-0")}>
              Create your free account
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function Cite({ n }: { n: number }) {
  return (
    <sup className="mx-0.5 rounded bg-accent-100 px-1 font-sans text-xs font-semibold text-accent-600">
      [{n}]
    </sup>
  );
}

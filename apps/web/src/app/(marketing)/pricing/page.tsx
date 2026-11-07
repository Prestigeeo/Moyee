import type { Metadata } from "next";
import Link from "next/link";
import { Check } from "lucide-react";
import { buttonClass, Card } from "@/components/ui";
import { FALLBACK_PLANS, PLAN_TAGLINES } from "@/config/plans";
import { apiFetch, type Plan } from "@/lib/api";

export const metadata: Metadata = { title: "Pricing" };
export const revalidate = 3600;

const STYLE_LABELS: Record<string, string> = {
  apa7: "APA 7",
  harvard: "Harvard",
  ieee: "IEEE",
  mla: "MLA",
  chicago: "Chicago",
};

async function getPlans(): Promise<Plan[]> {
  try {
    return await apiFetch<Plan[]>("/plans", null);
  } catch {
    return FALLBACK_PLANS;
  }
}

function limit(v: number | null | undefined, unit: string) {
  return v == null ? `Unlimited ${unit}` : `${v.toLocaleString()} ${unit}`;
}

function planLines(p: Plan): string[] {
  const l = p.limits;
  return [
    l.active_projects == null ? "Unlimited active projects" : `${l.active_projects} active projects`,
    limit(l.documents, "uploaded documents"),
    l.storage_mb != null && l.storage_mb >= 1024
      ? `${l.storage_mb / 1024} GB storage`
      : `${l.storage_mb} MB storage`,
    `${limit(l.assistant_messages, "assistant messages")} per day`,
    `${limit(l.academic_searches, "academic searches")}${l.academic_searches == null ? "" : " per day"}`,
    `${limit(l.document_summaries, "document summaries")} per month`,
    `Literature matrices with up to ${l.matrix_sources} sources`,
    `Citation styles: ${(p.features.citation_styles ?? []).map((s) => STYLE_LABELS[s] ?? s).join(", ")}`,
    `Export: ${(p.features.exports ?? []).map((e) => e.toUpperCase()).join(", ")}`,
  ];
}

export default async function PricingPage() {
  const plans = await getPlans();
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <div className="text-center">
        <h1 className="font-display text-4xl font-semibold md:text-5xl">Simple, student-friendly pricing</h1>
        <p className="mt-4 text-lg text-stone-600">Start free. Upgrade when your research grows.</p>
      </div>
      <div className="mt-14 grid gap-6 md:grid-cols-2">
        {plans.map((p) => {
          const pro = p.id === "pro";
          return (
            <Card key={p.id} className={pro ? "border-brand-600 p-8 ring-1 ring-brand-600" : "p-8"}>
              <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl font-semibold">{p.name}</h2>
                {pro && <span className="rounded-full bg-accent-100 px-3 py-1 text-xs font-semibold text-accent-600">Most popular</span>}
              </div>
              <p className="mt-2 text-sm text-stone-600">{PLAN_TAGLINES[p.id]}</p>
              <p className="mt-6">
                <span className="text-4xl font-semibold">${(p.price_usd_cents_monthly / 100).toFixed(0)}</span>
                <span className="text-stone-500"> / month</span>
              </p>
              {pro && (
                <p className="mt-1 text-sm text-stone-500">
                  or ${(p.price_usd_cents_yearly / 100).toFixed(0)}/year (save 20%)
                </p>
              )}
              <Link
                href="/sign-up"
                className={buttonClass(pro ? "primary" : "secondary", "lg", "mt-8 w-full")}
              >
                {pro ? "Start with Pro" : "Start free"}
              </Link>
              <ul className="mt-8 space-y-3 text-sm">
                {planLines(p).map((line) => (
                  <li key={line} className="flex gap-2">
                    <Check className="mt-0.5 size-4 shrink-0 text-brand-600" aria-hidden />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
      <p className="mt-10 text-center text-sm text-stone-500">
        Prices in USD. Local currency shown at checkout. Cancel anytime; Pro stays active until the end of the billing period.
      </p>
    </section>
  );
}

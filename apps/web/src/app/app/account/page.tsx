"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Badge, Button, Card, Input, Label, Select } from "@/components/ui";
import { CITATION_STYLES, RESEARCH_LEVELS } from "@/config/templates";
import {
  METRIC_LABELS,
  type CheckoutInit,
  type CitationStyle,
  type Profile,
  type ResearchLevel,
  type Usage,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";
import { createClient } from "@/lib/supabase/client";

export default function AccountPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [billingBusy, setBillingBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState("");

  useEffect(() => {
    Promise.all([browserApi<Profile>("/me"), browserApi<Usage>("/me/usage")])
      .then(([p, u]) => {
        setProfile(p);
        setUsage(u);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load account."));
  }, []);

  async function saveProfile(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const updated = await browserApi<Profile>("/me", {
        method: "PATCH",
        body: JSON.stringify({
          full_name: String(form.get("full_name") || "") || null,
          discipline: String(form.get("discipline") || "") || null,
          research_level: (form.get("research_level") as ResearchLevel) || null,
          default_citation_style: form.get("default_citation_style") as CitationStyle,
        }),
      });
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setSaving(false);
    }
  }

  async function upgradeToPro() {
    setBillingBusy(true);
    setError(null);
    try {
      await browserApi<CheckoutInit>("/billing/checkout", { method: "POST" });
      const refreshed = await browserApi<Usage>("/me/usage");
      setUsage(refreshed);
      router.refresh();
    } catch {
      setError("Could not start Pro upgrade.");
    } finally {
      setBillingBusy(false);
    }
  }

  async function cancelPro() {
    setBillingBusy(true);
    setError(null);
    try {
      const refreshed = await browserApi<Usage>("/billing/cancel", { method: "POST" });
      setUsage(refreshed);
      router.refresh();
    } catch {
      setError("Could not cancel subscription.");
    } finally {
      setBillingBusy(false);
    }
  }

  async function deleteAccount() {
    if (confirmDelete !== "DELETE") return;
    try {
      await browserApi("/me", { method: "DELETE" });
      await createClient().auth.signOut();
      router.replace("/");
    } catch {
      setError("Could not delete account.");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-6 py-10">
      <div>
        <h1 className="font-display text-3xl font-semibold">Account &amp; Plan</h1>
        <p className="mt-1 text-sm text-stone-600">
          Manage your profile, default research settings and subscription usage.
        </p>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {saved && <Alert tone="success">Profile saved.</Alert>}

      {/* Plan & Usage */}
      {usage && (
        <Card className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold">Current plan: {usage.plan.name}</h2>
                <Badge className="bg-brand-100 text-brand-800">{usage.subscription_status}</Badge>
              </div>
              <p className="mt-1 text-xs text-stone-500">
                {usage.plan.id === "free"
                  ? "Upgrade to Pro ($10/month) for unlimited active projects and higher daily limits."
                  : "You have full Pro access."}
              </p>
            </div>
            <div>
              {usage.plan.id === "free" ? (
                <Button type="button" size="sm" disabled={billingBusy} onClick={upgradeToPro}>
                  {billingBusy ? "Activating Pro…" : "Upgrade to Pro ($10/mo · Test Mode)"}
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={billingBusy}
                  onClick={cancelPro}
                >
                  Cancel Pro
                </Button>
              )}
            </div>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {usage.usage.map((item) => {
              const label = METRIC_LABELS[item.metric] ?? item.metric;
              const pct =
                item.limit && item.limit > 0
                  ? Math.min(100, Math.round((item.used / item.limit) * 100))
                  : 0;
              return (
                <div key={item.metric} className="rounded-lg border border-stone-200 p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-stone-700">{label}</span>
                    <span className="text-stone-500">
                      {item.used} / {item.limit ?? "∞"}
                    </span>
                  </div>
                  {item.limit != null && (
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-stone-100">
                      <div
                        className="h-full bg-brand-600 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Profile */}
      {profile && (
        <form onSubmit={saveProfile}>
          <Card className="space-y-4 p-6">
            <h2 className="font-semibold">Research profile</h2>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={profile.email ?? ""} disabled className="bg-stone-50" />
            </div>
            <div>
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" name="full_name" defaultValue={profile.full_name ?? ""} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="discipline">Primary discipline</Label>
                <Input id="discipline" name="discipline" defaultValue={profile.discipline ?? ""} />
              </div>
              <div>
                <Label htmlFor="research_level">Research level</Label>
                <Select
                  id="research_level"
                  name="research_level"
                  defaultValue={profile.research_level ?? "undergraduate"}
                >
                  {RESEARCH_LEVELS.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="default_citation_style">Default citation style</Label>
              <Select
                id="default_citation_style"
                name="default_citation_style"
                defaultValue={profile.default_citation_style}
              >
                {CITATION_STYLES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="pt-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save profile"}
              </Button>
            </div>
          </Card>
        </form>
      )}

      {/* Danger zone */}
      <Card className="border-red-200 p-6">
        <h2 className="font-semibold text-red-700">Delete account</h2>
        <p className="mt-1 text-sm text-stone-600">
          Permanently delete your profile, projects, sources and usage records. Type{" "}
          <strong>DELETE</strong> below to confirm.
        </p>
        <div className="mt-4 flex max-w-sm gap-3">
          <Input
            value={confirmDelete}
            onChange={(e) => setConfirmDelete(e.target.value)}
            placeholder="Type DELETE"
            aria-label="Type DELETE to confirm account deletion"
          />
          <Button
            type="button"
            variant="danger"
            disabled={confirmDelete !== "DELETE"}
            onClick={deleteAccount}
          >
            Delete
          </Button>
        </div>
      </Card>
    </div>
  );
}

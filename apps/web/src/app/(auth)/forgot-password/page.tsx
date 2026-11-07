"use client";

import { useState } from "react";
import Link from "next/link";
import { Alert, Button, Card, Input, Label } from "@/components/ui";
import { SITE_URL } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const email = String(new FormData(e.currentTarget).get("email"));
    const { error } = await createClient().auth.resetPasswordForEmail(email, {
      redirectTo: `${SITE_URL}/auth/callback?next=/reset-password`,
    });
    setLoading(false);
    // Don't reveal whether an account exists; only surface rate-limit style errors.
    if (error && error.status === 429) setError("Too many attempts. Please wait a minute and try again.");
    else setSent(true);
  }

  return (
    <Card className="p-6">
      <h1 className="font-display text-2xl font-semibold">Reset your password</h1>
      {sent ? (
        <Alert tone="success" className="mt-4">
          If an account exists for that email, we’ve sent a reset link.
        </Alert>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {error && <Alert tone="error">{error}</Alert>}
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" name="email" type="email" autoComplete="email" required />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
      <p className="mt-6 text-center text-sm">
        <Link href="/sign-in" className="font-medium text-brand-600 hover:underline">Back to sign in</Link>
      </p>
    </Card>
  );
}

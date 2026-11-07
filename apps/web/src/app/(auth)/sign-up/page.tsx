"use client";

import { useState } from "react";
import Link from "next/link";
import { MailCheck } from "lucide-react";
import { Alert, Button, Card, Input, Label } from "@/components/ui";
import { SITE_URL } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";

export default function SignUpPage() {
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    const email = String(form.get("email"));
    const password = String(form.get("password"));
    if (password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    setLoading(true);
    const { error } = await createClient().auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${SITE_URL}/auth/callback?next=/app`,
        data: { full_name: String(form.get("name") || "") },
      },
    });
    setLoading(false);
    if (error) {
      setError(error.message);
      return;
    }
    setSentTo(email);
  }

  if (sentTo) {
    return (
      <Card className="p-6 text-center">
        <MailCheck className="mx-auto size-10 text-brand-600" aria-hidden />
        <h1 className="mt-4 font-display text-2xl font-semibold">Check your email</h1>
        <p className="mt-2 text-sm text-stone-600">
          We sent a verification link to <strong>{sentTo}</strong>. Open it to activate your account.
        </p>
        <Link href="/sign-in" className="mt-6 inline-block text-sm font-medium text-brand-600 hover:underline">
          Back to sign in
        </Link>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h1 className="font-display text-2xl font-semibold">Create your account</h1>
      <p className="mt-1 text-sm text-stone-600">Free to start. No card required.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <div>
          <Label htmlFor="name">Full name</Label>
          <Input id="name" name="name" autoComplete="name" />
        </div>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" type="email" autoComplete="email" required />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required />
          <p className="mt-1 text-xs text-stone-500">At least 8 characters.</p>
        </div>
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-xs text-stone-500">
          By creating an account you agree to our <Link href="/terms" className="underline">Terms</Link> and{" "}
          <Link href="/privacy" className="underline">Privacy Policy</Link>.
        </p>
      </form>
      <p className="mt-6 text-center text-sm text-stone-600">
        Already have an account?{" "}
        <Link href="/sign-in" className="font-medium text-brand-600 hover:underline">Sign in</Link>
      </p>
    </Card>
  );
}

"use client";

import { apiFetch } from "@/lib/api";
import { isAuthConfigured } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";

/** Authenticated API call from a Client Component. */
export async function browserApi<T>(path: string, init?: RequestInit): Promise<T> {
  if (!isAuthConfigured) {
    return apiFetch<T>(path, "local-dev-token", init);
  }
  const {
    data: { session },
  } = await createClient().auth.getSession();
  return apiFetch<T>(path, session?.access_token ?? null, init);
}

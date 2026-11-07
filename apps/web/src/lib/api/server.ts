import "server-only";
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { isAuthConfigured } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";

/** Authenticated API call from a Server Component. */
export async function serverApi<T>(path: string, init?: RequestInit): Promise<T> {
  if (!isAuthConfigured) {
    return apiFetch<T>(path, "local-dev-token", init);
  }
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) redirect("/sign-in");
  return apiFetch<T>(path, session.access_token, init);
}

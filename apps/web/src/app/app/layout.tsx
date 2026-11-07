import Link from "next/link";
import { User } from "lucide-react";
import { Wordmark } from "@/components/brand/wordmark";
import { Badge, buttonClass } from "@/components/ui";
import { serverApi } from "@/lib/api/server";
import type { Usage } from "@/lib/api";

async function loadUsage(): Promise<Usage | null> {
  try {
    return await serverApi<Usage>("/me/usage");
  } catch {
    return null;
  }
}

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const usage = await loadUsage();
  const messagesItem = usage?.usage.find((u) => u.metric === "assistant_messages");

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Wordmark href="/app" className="text-xl" />
            <nav className="hidden items-center gap-4 text-sm text-stone-600 sm:flex" aria-label="Workspace">
              <Link href="/app" className="hover:text-ink">Projects</Link>
              <Link href="/app/projects/new" className="hover:text-ink">New project</Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {usage && (
              <Link
                href="/app/account"
                className="hidden items-center gap-2 rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs text-stone-700 hover:bg-stone-100 sm:inline-flex"
              >
                <Badge className="bg-brand-100 text-brand-800">{usage.plan.name}</Badge>
                {messagesItem && (
                  <span>
                    {messagesItem.used}
                    {messagesItem.limit != null ? `/${messagesItem.limit}` : ""} messages today
                  </span>
                )}
              </Link>
            )}
            <Link href="/app/account" className={buttonClass("ghost", "sm")} aria-label="Account settings">
              <User className="size-4" aria-hidden />
              <span className="hidden sm:inline">Account</span>
            </Link>
            <form action="/auth/sign-out" method="post">
              <button type="submit" className={buttonClass("ghost", "sm")}>
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}

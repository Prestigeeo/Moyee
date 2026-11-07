import Link from "next/link";
import { Wordmark } from "@/components/brand/wordmark";
import { buttonClass } from "@/components/ui";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-stone-200/70 bg-canvas/85 backdrop-blur">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6" aria-label="Main">
          <Wordmark />
          <div className="hidden items-center gap-8 text-sm text-stone-600 md:flex">
            <Link href="/#features" className="hover:text-ink">Features</Link>
            <Link href="/#how-it-works" className="hover:text-ink">How it works</Link>
            <Link href="/pricing" className="hover:text-ink">Pricing</Link>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/sign-in" className={buttonClass("ghost", "sm")}>Sign in</Link>
            <Link href="/sign-up" className={buttonClass("primary", "sm")}>Start free</Link>
          </div>
        </nav>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 text-sm text-stone-500 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <Wordmark className="text-lg" />
            <span>© {new Date().getFullYear()} Móyee</span>
          </div>
          <div className="flex gap-6">
            <Link href="/pricing" className="hover:text-ink">Pricing</Link>
            <Link href="/privacy" className="hover:text-ink">Privacy</Link>
            <Link href="/terms" className="hover:text-ink">Terms</Link>
            <a href="mailto:hello@moyee.app" className="hover:text-ink">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

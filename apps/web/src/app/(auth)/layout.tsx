import Link from "next/link";
import { Wordmark } from "@/components/brand/wordmark";
import { Alert } from "@/components/ui";
import { isAuthConfigured } from "@/lib/env";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 py-12">
      <Wordmark className="text-3xl" />
      <div className="mt-8 w-full max-w-sm">
        {!isAuthConfigured && (
          <Alert tone="info" className="mb-4">
            Running in local preview mode.{" "}
            <Link href="/app" className="font-semibold underline">
              Continue directly to the workspace →
            </Link>
          </Alert>
        )}
        {children}
      </div>
      <p className="mt-10 text-xs text-stone-500">
        <Link href="/terms" className="hover:underline">Terms</Link> ·{" "}
        <Link href="/privacy" className="hover:underline">Privacy</Link>
      </p>
    </div>
  );
}

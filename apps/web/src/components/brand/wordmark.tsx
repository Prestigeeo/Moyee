import Link from "next/link";
import { BRAND_NAME } from "@/config/brand";
import { cn } from "@/lib/utils";

export function Wordmark({ className, href = "/" }: { className?: string; href?: string | null }) {
  const mark = (
    <span className={cn("font-display text-2xl font-semibold tracking-tight text-brand-700", className)}>
      {BRAND_NAME}
    </span>
  );
  return href ? (
    <Link href={href} aria-label={`${BRAND_NAME} home`}>
      {mark}
    </Link>
  ) : (
    mark
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookMarked,
  Compass,
  FileSearch,
  Layers,
  Library,
  PenLine,
  Settings,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function ProjectSidebar({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  const base = `/app/p/${projectId}`;

  const items = [
    { href: base, label: "Overview", icon: Compass, exact: true },
    { href: `${base}/discover`, label: "Discover", icon: FileSearch },
    { href: `${base}/library`, label: "Library", icon: Library },
    { href: `${base}/assistant`, label: "Assistant", icon: Sparkles },
    { href: `${base}/literature`, label: "Literature", icon: Layers },
    { href: `${base}/write`, label: "Write", icon: PenLine },
    { href: `${base}/references`, label: "References", icon: BookMarked },
    { href: `${base}/settings`, label: "Settings", icon: Settings },
  ];

  return (
    <aside className="w-full border-b border-stone-200 bg-white md:w-56 md:shrink-0 md:border-b-0 md:border-r">
      <nav className="flex gap-1 overflow-x-auto p-3 md:flex-col" aria-label="Project modules">
        {items.map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-stone-600 hover:bg-stone-100 hover:text-ink",
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

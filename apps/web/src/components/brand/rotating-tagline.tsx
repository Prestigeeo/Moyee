"use client";

import { useEffect, useState } from "react";
import { STATIC_TAGLINE, TAGLINES, TAGLINE_INTERVAL_MS } from "@/config/brand";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  intervalMs?: number;
  taglines?: readonly string[];
};

/**
 * Rotating landing-page tagline (PRD §14.3).
 * - Rotates every `intervalMs` (default 20 s from config).
 * - Static fallback when the user prefers reduced motion (and server-rendered for no-JS).
 * - Pauses while the tab is hidden so users don't come back to a skipped sequence.
 * - Announced politely to assistive technologies.
 */
export function RotatingTagline({
  className,
  intervalMs = TAGLINE_INTERVAL_MS,
  taglines = TAGLINES,
}: Props) {
  const [index, setIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (reducedMotion || taglines.length < 2) return;
    let timer: ReturnType<typeof setInterval> | undefined;
    const start = () => {
      timer = setInterval(() => setIndex((i) => (i + 1) % taglines.length), intervalMs);
    };
    const stop = () => timer && clearInterval(timer);
    const onVisibility = () => (document.hidden ? stop() : start());
    start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [reducedMotion, intervalMs, taglines.length]);

  const text = reducedMotion ? STATIC_TAGLINE : taglines[index];

  return (
    <p className={cn("min-h-[1.5em]", className)} aria-live="polite" aria-atomic="true">
      <span key={text} className="tagline-enter inline-block">
        {text}
      </span>
    </p>
  );
}

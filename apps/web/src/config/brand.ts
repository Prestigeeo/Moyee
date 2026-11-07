export const BRAND_NAME = "Móyee";

/** Single source of truth for the tagline rotation (PRD §14.3). */
export const TAGLINE_INTERVAL_MS = 20_000;

export const TAGLINES = [
  "Research with clarity.",
  "From curiosity to knowledge.",
  "Discover what the evidence reveals.",
  "Turn questions into insights.",
  "Your ideas. Better research.",
  "Knowledge, intelligently connected.",
] as const;

/** Shown when motion is reduced or JavaScript is unavailable. */
export const STATIC_TAGLINE = TAGLINES[0];

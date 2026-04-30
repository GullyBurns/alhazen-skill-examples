// Shared design tokens — Starry Night identity palette.
// bg #070d1c | card #0c1628 | fg #c8dde8 | muted-fg #8ba4b8
// teal #5aadaf (primary) | dusty-blue #5b8ab8 | olive #b8c84a (accent) | mint #62c4bc

export const TOKENS = {
  bg:        '#070d1c',
  bgRaised:  '#0c1628',
  bgSunken:  '#050a16',
  panel:     'rgba(12, 22, 40, 0.72)',
  panelHi:   'rgba(20, 34, 58, 0.85)',
  border:    'rgba(90, 173, 175, 0.18)',
  borderHi:  'rgba(90, 173, 175, 0.42)',
  borderDim: 'rgba(200, 221, 232, 0.08)',
  fg:        '#c8dde8',
  fgDim:     '#8ba4b8',
  fgFaint:   '#5e7387',
  teal:      '#5aadaf',
  tealDim:   'rgba(90, 173, 175, 0.18)',
  blue:      '#5b8ab8',
  blueDim:   'rgba(91, 138, 184, 0.18)',
  olive:     '#b8c84a',
  oliveDim:  'rgba(184, 200, 74, 0.18)',
  mint:      '#62c4bc',
  rust:      '#c87a4a',
  rustDim:   'rgba(200, 122, 74, 0.18)',
  mono:      'ui-monospace, "JetBrains Mono", "SF Mono", Menlo, monospace',
  serif:     '"DM Serif Display", "Iowan Old Style", Georgia, serif',
  sans:      '"DM Sans", -apple-system, system-ui, sans-serif',
} as const;

export type TokenKey = keyof typeof TOKENS;

// Subtype catalogue
export const SUBTYPES = {
  position:   { label: 'Position',   icon: 'square',   color: TOKENS.teal,  short: 'POS' },
  engagement: { label: 'Engagement', icon: 'diamond',  color: TOKENS.blue,  short: 'ENG' },
  venture:    { label: 'Venture',    icon: 'triangle', color: TOKENS.olive, short: 'VEN' },
  lead:       { label: 'Lead',       icon: 'circle',   color: TOKENS.mint,  short: 'LED' },
} as const;

export type SubtypeKey = keyof typeof SUBTYPES;

// Application status order
export const STATUS_ORDER = [
  'researching',
  'applied',
  'phone-screen',
  'interviewing',
  'offer',
  'rejected',
  'withdrawn',
] as const;

export type StatusKey = typeof STATUS_ORDER[number];

// Action-engine urgency colors
export const URGENCY = {
  high:   { color: TOKENS.olive, label: 'now' },
  medium: { color: TOKENS.teal,  label: 'soon' },
  low:    { color: TOKENS.fgDim, label: 'later' },
} as const;

export type UrgencyKey = keyof typeof URGENCY;

// --- Date helpers ---

/** Days between an ISO date string and today (positive = future, negative = past). */
export function daysBetween(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  return Math.round(ms / 86_400_000);
}

/** Format an ISO date string as "Mon D" (e.g. "Apr 30"). */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** Human-relative label: "today", "tomorrow", "3d ago", "in 5d". */
export function relDate(iso: string | null | undefined): string {
  const d = daysBetween(iso);
  if (d === null) return '\u2014';
  if (d === 0) return 'today';
  if (d === 1) return 'tomorrow';
  if (d === -1) return 'yesterday';
  if (d > 0) return `in ${d}d`;
  return `${-d}d ago`;
}

/** Format an ISO timestamp as a locale date+time string. */
export function fmtTimestamp(iso: string | null | undefined): string {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/** Days until an ISO date (positive = future). Alias of daysBetween. */
export function daysUntil(iso: string | null | undefined): number | null {
  return daysBetween(iso);
}

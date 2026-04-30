'use client';

// In Play — consumes `list-attention` JSON directly.
//
// Every lead the operator is actively working. Pre-sorted by the CLI on
// priority. Dashboard groups visually by where the next move sits:
//   ▸ Fresh from CC    new cc-brief or pending operator feedback
//   ▸ Your move        a clear next step is on you
//   ▸ Waiting          the ball is in their court — this is normal
//
// Grouping is derived from the raw fields — no schema additions needed.
// Tone matters: job hunting is stressful enough; the design avoids
// stress-coded colors (rust/red) for things that are not actually wrong.

import React, { CSSProperties } from 'react';
import { useRouter } from 'next/navigation';
import { TOKENS } from './tokens';
import { Icon, SchemaTag } from './icons';

const TI = TOKENS;

// --- Types ---

export interface OpportunityItem {
  id: string;
  type: 'jobhunt-position' | 'jobhunt-engagement' | 'jobhunt-venture' | 'jobhunt-lead';
  name: string;
  company: string;
  status: string;
  priority: 'high' | 'medium' | 'low';
  deadline?: string | null;
  latest_cc_brief?: string | null;
  pending_feedback_count: number;
  days_since_last_touch: number;
}

interface KindMeta {
  short: string;
  color: string;
  icon: string;
}

// --- KIND_META ---

const KIND_META: Record<string, KindMeta> = {
  'jobhunt-position':   { short: 'POS', color: TI.teal,  icon: 'square' },
  'jobhunt-engagement': { short: 'ENG', color: TI.blue,  icon: 'diamond' },
  'jobhunt-venture':    { short: 'VEN', color: TI.olive, icon: 'triangle' },
  'jobhunt-lead':       { short: 'LED', color: TI.mint,  icon: 'circle' },
};

// --- fmtRel ---

const fmtRel = (iso: string | null | undefined): string => {
  if (!iso) return '—';
  const days = Math.round((new Date().getTime() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return '1d';
  return `${days}d`;
};

// --- fmtDeadline ---

const fmtDeadline = (iso: string | null | undefined): { text: string; urgent: boolean } | null => {
  if (!iso) return null;
  const days = Math.round((new Date(iso).getTime() - new Date().getTime()) / 86_400_000);
  if (days < 0) return { text: `${-days}d ago`, urgent: true };
  if (days === 0) return { text: 'today', urgent: true };
  if (days <= 7) return { text: `in ${days}d`, urgent: true };
  return { text: `in ${days}d`, urgent: false };
};

// --- PriorityDot ---

interface PriorityDotProps {
  priority: 'high' | 'medium' | 'low';
}

function PriorityDot({ priority }: PriorityDotProps) {
  const c = priority === 'high' ? TI.olive : priority === 'medium' ? TI.teal : TI.fgFaint;
  return (
    <span title={`priority: ${priority}`} style={{
      display: 'inline-block', width: 7, height: 7, borderRadius: 4,
      background: priority === 'high' ? c : 'transparent',
      border: `1.5px solid ${c}`,
    }} />
  );
}

// --- StatusBadge ---

interface StatusBadgeProps {
  status: string;
  dim: boolean;
}

function StatusBadge({ status, dim }: StatusBadgeProps) {
  return (
    <span style={{
      fontFamily: TI.mono, fontSize: 9.5, letterSpacing: 0.8, textTransform: 'uppercase',
      padding: '1.5px 7px', borderRadius: 2,
      color: dim ? TI.fgFaint : TI.fgDim,
      border: `1px solid ${dim ? TI.borderDim : TI.border}`,
      whiteSpace: 'nowrap',
    }}>{status}</span>
  );
}

// --- bucket ---

type BucketKey = 'cc' | 'you' | 'waiting';

function bucket(o: OpportunityItem): BucketKey {
  const briefAge = o.latest_cc_brief
    ? Math.round((new Date().getTime() - new Date(o.latest_cc_brief).getTime()) / 86_400_000)
    : null;
  // Fresh from CC: brief is recent, OR there's pending feedback, OR no brief yet (CC owes you one).
  if (o.pending_feedback_count > 0) return 'cc';
  if (briefAge === null) return 'cc';
  if (briefAge <= 3) return 'cc';
  // Otherwise: if it's been >7d since any touch, you're waiting on them. Else your move.
  if (o.days_since_last_touch > 7) return 'waiting';
  return 'you';
}

// --- Row ---

interface RowProps {
  o: OpportunityItem;
  onOpen: () => void;
  openable: boolean;
}

function Row({ o, onOpen, openable }: RowProps) {
  const meta = KIND_META[o.type] || KIND_META['jobhunt-position'];
  const deadline = fmtDeadline(o.deadline);

  return (
    <li
      onClick={openable ? onOpen : undefined}
      style={{
        display: 'grid',
        gridTemplateColumns: '14px 56px 1fr auto auto auto',
        gap: 14, alignItems: 'center',
        padding: '10px 14px',
        borderTop: `1px solid ${TI.borderDim}`,
        cursor: openable ? 'pointer' : 'default',
        background: 'transparent',
        transition: 'background 0.12s',
      }}
      onMouseEnter={(e) => { if (openable) e.currentTarget.style.background = 'rgba(90,173,175,0.06)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      <PriorityDot priority={o.priority} />
      <span style={{
        fontFamily: TI.mono, fontSize: 9.5, letterSpacing: 1, fontWeight: 600,
        color: meta.color, display: 'inline-flex', alignItems: 'center', gap: 4,
      }}>
        <Icon name={meta.icon} size={10} color={meta.color} />
        {meta.short}
      </span>

      <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 13.5, color: TI.fg, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {o.name}
        </span>
        <span style={{ fontFamily: TI.mono, fontSize: 10.5, color: TI.fgFaint }}>
          {o.company}
        </span>
      </div>

      {/* Brief / feedback signal */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TI.mono, fontSize: 10.5 }}>
        {o.latest_cc_brief ? (
          <span style={{ color: TI.fgDim }} title={`latest cc-brief-note · ${fmtRel(o.latest_cc_brief)} ago`}>
            <Icon name="sparkles" size={10} color={TI.olive} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            brief {fmtRel(o.latest_cc_brief)}
          </span>
        ) : (
          <span style={{ color: TI.fgDim }} title="no cc-brief-note yet">
            <Icon name="sparkles" size={10} color={TI.fgDim} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            awaiting brief
          </span>
        )}
        {o.pending_feedback_count > 0 && (
          <span style={{ color: TI.teal }} title="cc-feedback-notes newer than latest brief">
            <Icon name="message" size={10} color={TI.teal} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            {o.pending_feedback_count} fb
          </span>
        )}
      </div>

      <StatusBadge status={o.status} dim={!openable} />

      {deadline && (
        <span style={{
          fontFamily: TI.mono, fontSize: 10.5,
          color: deadline.urgent ? TI.olive : TI.fgFaint,
          whiteSpace: 'nowrap', minWidth: 64, textAlign: 'right',
        }}>{deadline.text}</span>
      )}
      {!deadline && <span style={{ minWidth: 64 }} />}
    </li>
  );
}

// --- GroupHeader ---

interface GroupHeaderProps {
  label: string;
  hint: string;
  count: number;
}

function GroupHeader({ label, hint, count }: GroupHeaderProps) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 12,
      padding: '14px 14px 8px',
    }}>
      <h3 style={{
        margin: 0, fontFamily: TI.mono, fontSize: 10.5, fontWeight: 600,
        letterSpacing: 1.4, textTransform: 'uppercase', color: TI.fg,
      }}>{label}</h3>
      <span style={{ fontFamily: TI.mono, fontSize: 10.5, color: TI.fgFaint }}>{count}</span>
      <span style={{ flex: 1 }} />
      <span style={{ fontFamily: TI.mono, fontSize: 10, color: TI.fgFaint, fontStyle: 'italic' }}>{hint}</span>
    </div>
  );
}

// --- TriageInbox ---

export interface TriageInboxProps {
  items: OpportunityItem[];
  dossierIds?: string[];
  onOpen?: (id: string) => void;
}

export function TriageInbox({ items, dossierIds = [], onOpen }: TriageInboxProps) {
  const router = useRouter();
  const groups: Record<BucketKey, OpportunityItem[]> = { cc: [], you: [], waiting: [] };
  items.forEach((o) => groups[bucket(o)].push(o));

  const handleOpen = (id: string) => {
    if (onOpen) {
      onOpen(id);
    } else {
      router.push(`/jobhunt/opportunity/${id}`);
    }
  };

  return (
    <div style={{
      padding: 20, height: '100%', overflow: 'auto',
      background: TI.bg, color: TI.fg, fontFamily: TI.sans,
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'baseline', gap: 12, padding: '4px 4px 0' }}>
        <h1 style={{
          margin: 0, fontFamily: TI.serif, fontSize: 26, fontWeight: 400,
          color: TI.fg, letterSpacing: -0.4,
        }}>In play</h1>
        <span style={{ fontFamily: TI.mono, fontSize: 11, color: TI.fgDim }}>
          {items.length} {items.length === 1 ? 'lead' : 'leads'} · sorted by priority
        </span>
        <span style={{ flex: 1 }} />
        <SchemaTag type="list-attention" />
      </header>

      <p style={{ margin: 0, padding: '0 4px', fontSize: 13, lineHeight: 1.55, color: TI.fgDim, maxWidth: 720 }}>
        Every lead you are actively working. The first group is where CC has fresh thinking for you to read;
        the second is where you can pick up and move; the last is where you are waiting on someone else and that is fine.
      </p>

      {/* CC has fresh thinking */}
      {groups.cc.length > 0 && (
        <section style={{
          background: 'rgba(98,196,188,0.04)',
          border: `1px solid rgba(98,196,188,0.32)`,
          borderRadius: 4,
        }}>
          <GroupHeader label="Fresh from CC" hint="new brief or your feedback to read" count={groups.cc.length} />
          <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {groups.cc.map((o) => (
              <Row key={o.id} o={o} openable={dossierIds.includes(o.id)} onOpen={() => handleOpen(o.id)} />
            ))}
          </ol>
        </section>
      )}

      {/* You move */}
      {groups.you.length > 0 && (
        <section style={{
          background: TI.panel,
          border: `1px solid ${TI.border}`,
          borderRadius: 4,
        }}>
          <GroupHeader label="Your move" hint="a clear next step is on you" count={groups.you.length} />
          <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {groups.you.map((o) => (
              <Row key={o.id} o={o} openable={dossierIds.includes(o.id)} onOpen={() => handleOpen(o.id)} />
            ))}
          </ol>
        </section>
      )}

      {/* Waiting — no negative tinting; this is normal */}
      {groups.waiting.length > 0 && (
        <section style={{
          background: TI.panel,
          border: `1px solid ${TI.borderDim}`,
          borderRadius: 4,
        }}>
          <GroupHeader label="Waiting" hint="the ball is in their court" count={groups.waiting.length} />
          <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {groups.waiting.map((o) => (
              <Row key={o.id} o={o} openable={dossierIds.includes(o.id)} onOpen={() => handleOpen(o.id)} />
            ))}
          </ol>
        </section>
      )}

      {/* Legend */}
      <footer style={{
        marginTop: 8, paddingTop: 12, borderTop: `1px solid ${TI.borderDim}`,
        display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap',
        fontFamily: TI.mono, fontSize: 10, color: TI.fgFaint,
      }}>
        <span>shape: list-attention --json</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <PriorityDot priority="high" /> high
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <PriorityDot priority="medium" /> medium
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <PriorityDot priority="low" /> low
        </span>
        <span>·</span>
        <span><Icon name="sparkles" size={10} color={TI.olive} style={{ verticalAlign: 'middle', marginRight: 3 }} /> cc-brief-note age</span>
        <span><Icon name="message" size={10} color={TI.teal} style={{ verticalAlign: 'middle', marginRight: 3 }} /> pending feedback notes</span>
      </footer>
    </div>
  );
}

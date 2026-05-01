'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export interface MapItem {
  id: string;
  short_name: string;
  company: string;
  status: string;
  priority: string | null;
  type: string;
  x: number;
  y: number;
  notes_count?: number;
  name?: string;
}

interface OpportunityListProps {
  items: MapItem[];
  visibleIds: Set<string>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFilterChange?: (filteredIds: Set<string>) => void;
}

const PRIORITY_ORDER: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

const STATUS_ORDER: Record<string, number> = {
  researching: 0,
  applied: 1,
  interviewing: 2,
  offer: 3,
  rejected: 4,
  withdrawn: 5,
};

const PRIORITY_COLORS: Record<string, string> = {
  high: '#e05555',
  medium: '#d4a843',
  low: '#5aadaf',
};

const TYPE_LABELS: Record<string, string> = {
  position: 'POS',
  engagement: 'ENG',
  venture: 'VEN',
  lead: 'LED',
};

const STATUS_COLORS: Record<string, string> = {
  interviewing: '#5aadaf',
  applied: '#5b8ab8',
  researching: '#8ba4b8',
  withdrawn: '#5e7387',
  rejected: '#5e7387',
};

function getPrioritySort(p: string | null): number {
  if (!p) return 3;
  return PRIORITY_ORDER[p] ?? 3;
}

function getStatusSort(s: string): number {
  return STATUS_ORDER[s] ?? 3;
}

const TYPE_COLORS: Record<string, string> = {
  position: '#5aadaf',
  engagement: '#5b8ab8',
  venture: '#b8c84a',
  lead: '#62c4bc',
};

// Default: show everything except withdrawn and rejected
const DEFAULT_OFF_STATUSES = new Set(['withdrawn', 'rejected']);
// All possible statuses in pipeline order (so withdrawn shows even if no items yet)
const ALL_STATUSES = ['researching', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn'];

export function OpportunityList({ items, visibleIds, selectedId, onSelect, onFilterChange }: OpportunityListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string> | null>(null);
  const [activeStatuses, setActiveStatuses] = useState<Set<string> | null>(null);
  const router = useRouter();

  // Compute available types and statuses from visible items
  const visibleItems = items.filter(item => visibleIds.has(item.id));
  const types = Array.from(new Set(visibleItems.map(i => i.type))).sort();
  const presentStatuses = Array.from(new Set(visibleItems.map(i => i.status).filter(Boolean)));
  // Show all pipeline statuses that have data
  const statuses = ALL_STATUSES.filter(s => presentStatuses.includes(s));

  // Initialize on first data load via useEffect (not during render)
  useEffect(() => {
    if (activeTypes === null && types.length > 0) {
      setActiveTypes(new Set(types));
    }
    if (activeStatuses === null && statuses.length > 0) {
      const initial = new Set(statuses.filter(s => !DEFAULT_OFF_STATUSES.has(s)));
      setActiveStatuses(initial);
      // Defer parent notification to avoid update-during-render
      if (onFilterChange) {
        setTimeout(() => {
          const ids = new Set(
            visibleItems
              .filter(item => initial.has(item.status || ''))
              .map(item => item.id)
          );
          onFilterChange(ids);
        }, 0);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.length]);

  const typesOn = activeTypes || new Set(types);
  const statusesOn = activeStatuses || new Set(statuses.filter(s => !DEFAULT_OFF_STATUSES.has(s)));

  const filtered = visibleItems
    .filter(item => typesOn.has(item.type))
    .filter(item => !item.status || statusesOn.has(item.status))
    .sort((a, b) => {
      const pDiff = getPrioritySort(a.priority) - getPrioritySort(b.priority);
      if (pDiff !== 0) return pDiff;
      return getStatusSort(a.status) - getStatusSort(b.status);
    });

  const notifyFilter = (newTypes: Set<string>, newStatuses: Set<string>) => {
    if (onFilterChange) {
      const ids = new Set(
        visibleItems
          .filter(item => newTypes.has(item.type))
          .filter(item => !item.status || newStatuses.has(item.status))
          .map(item => item.id)
      );
      onFilterChange(ids);
    }
  };

  const toggleType = (t: string) => {
    const next = new Set(typesOn);
    if (next.has(t)) { next.delete(t); } else { next.add(t); }
    setActiveTypes(next);
    notifyFilter(next, statusesOn);
  };

  const toggleStatus = (s: string) => {
    const next = new Set(statusesOn);
    if (next.has(s)) { next.delete(s); } else { next.add(s); }
    setActiveStatuses(next);
    notifyFilter(typesOn, next);
  };

  const handleClick = (id: string) => {
    onSelect(id);
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div style={{
      overflowY: 'auto',
      height: '100%',
      fontFamily: "'DM Sans', sans-serif",
    }}>
      {/* Filter toggles */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid rgba(94, 115, 135, 0.2)',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '4px',
        alignItems: 'center',
      }}>
        {/* Type toggles */}
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5e7387', marginRight: '2px' }}>TYPE</span>
        {types.map(t => (
          <FilterChip
            key={t}
            label={TYPE_LABELS[t] || t}
            active={typesOn.has(t)}
            onClick={() => toggleType(t)}
            color={TYPE_COLORS[t] || '#8ba4b8'}
            count={visibleItems.filter(i => i.type === t).length}
          />
        ))}
        <span style={{ width: '1px', height: '16px', background: 'rgba(94,115,135,0.3)', margin: '0 6px' }} />
        {/* Status toggles */}
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: '#5e7387', marginRight: '2px' }}>STATUS</span>
        {statuses.map(s => (
          <FilterChip
            key={s}
            label={s}
            active={statusesOn.has(s)}
            onClick={() => toggleStatus(s)}
            color={STATUS_COLORS[s] || '#8ba4b8'}
            count={visibleItems.filter(i => i.status === s).length}
          />
        ))}
      </div>

      <div style={{ fontSize: '10px', color: '#5e7387', padding: '4px 12px', fontFamily: "'JetBrains Mono', monospace" }}>
        {filtered.length} of {visibleItems.length} shown
      </div>

      {filtered.length === 0 && (
        <div style={{
          color: '#5e7387',
          textAlign: 'center',
          padding: '40px 16px',
          fontSize: '13px',
        }}>
          No items visible
        </div>
      )}
      {filtered.map(item => {
        const isSelected = selectedId === item.id;
        const isExpanded = expandedId === item.id;
        const priorityColor = PRIORITY_COLORS[item.priority || ''] || '#5e7387';
        const typeLabel = TYPE_LABELS[item.type] || item.type?.toUpperCase()?.slice(0, 3) || '---';
        const statusColor = STATUS_COLORS[item.status] || '#5e7387';

        return (
          <div
            key={item.id}
            onClick={() => handleClick(item.id)}
            style={{
              padding: '8px 12px',
              borderLeft: isSelected ? '2px solid #5aadaf' : '2px solid transparent',
              borderBottom: '1px solid rgba(94, 115, 135, 0.2)',
              cursor: 'pointer',
              backgroundColor: isSelected ? 'rgba(90, 173, 175, 0.06)' : 'transparent',
              transition: 'background-color 0.15s',
            }}
            onMouseEnter={(e) => {
              if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(90, 173, 175, 0.03)';
            }}
            onMouseLeave={(e) => {
              if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Priority dot */}
              <div style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: priorityColor,
                flexShrink: 0,
              }} />

              {/* Type badge */}
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '9px',
                color: '#8ba4b8',
                border: '1px solid rgba(139, 164, 184, 0.3)',
                borderRadius: '3px',
                padding: '1px 4px',
                letterSpacing: '0.5px',
                flexShrink: 0,
              }}>
                {typeLabel}
              </span>

              {/* Short name */}
              <span style={{
                fontSize: '13px',
                color: '#c8dde8',
                fontFamily: "'DM Sans', sans-serif",
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                flex: 1,
              }}>
                {item.short_name}
              </span>

              {/* Company */}
              <span style={{
                fontSize: '12px',
                color: '#5e7387',
                fontFamily: "'DM Sans', sans-serif",
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '120px',
                flexShrink: 0,
              }}>
                {item.company}
              </span>

              {/* Status badge */}
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '9px',
                color: statusColor,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                flexShrink: 0,
              }}>
                {item.status}
              </span>
            </div>

            {/* Expanded detail */}
            {isExpanded && (
              <div style={{
                marginTop: '8px',
                paddingLeft: '15px',
                fontSize: '12px',
                color: '#8ba4b8',
                lineHeight: '1.6',
              }}>
                <div><span style={{ color: '#5e7387' }}>Full name:</span> {item.name || item.short_name}</div>
                <div><span style={{ color: '#5e7387' }}>Company:</span> {item.company}</div>
                <div><span style={{ color: '#5e7387' }}>Type:</span> {item.type}</div>
                {item.notes_count !== undefined && (
                  <div><span style={{ color: '#5e7387' }}>Notes:</span> {item.notes_count}</div>
                )}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/jobhunt/opportunity/${item.id}`);
                  }}
                  style={{
                    marginTop: '6px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '11px',
                    color: '#5aadaf',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = '#b8c84a'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = '#5aadaf'; }}
                >
                  View dossier →
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function FilterChip({ label, active, onClick, color, count }: { label: string; active: boolean; onClick: () => void; color: string; count?: number }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9.5px',
        letterSpacing: '0.4px',
        padding: '2px 7px',
        borderRadius: '3px',
        cursor: 'pointer',
        background: active ? color : 'transparent',
        color: active ? '#070d1c' : color,
        border: `1px solid ${active ? color : 'rgba(200,221,232,0.12)'}`,
        textTransform: 'lowercase',
        opacity: active ? 1 : 0.5,
      }}
    >
      {label}
      {count !== undefined && (
        <span style={{ opacity: 0.6, marginLeft: '3px' }}>{count}</span>
      )}
    </button>
  );
}

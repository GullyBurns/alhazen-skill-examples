'use client';

import { useState } from 'react';

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
}

const PRIORITY_ORDER: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

const STATUS_ORDER: Record<string, number> = {
  interviewing: 0,
  applied: 1,
  researching: 2,
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

export function OpportunityList({ items, visibleIds, selectedId, onSelect }: OpportunityListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const visible = items
    .filter(item => visibleIds.has(item.id))
    .sort((a, b) => {
      const pDiff = getPrioritySort(a.priority) - getPrioritySort(b.priority);
      if (pDiff !== 0) return pDiff;
      return getStatusSort(a.status) - getStatusSort(b.status);
    });

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
      {visible.length === 0 && (
        <div style={{
          color: '#5e7387',
          textAlign: 'center',
          padding: '40px 16px',
          fontSize: '13px',
        }}>
          No items visible
        </div>
      )}
      {visible.map(item => {
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
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

'use client';

import { useState, useEffect, useCallback } from 'react';
import { EmbeddingMap, MapItem } from '@/components/jobhunt/embedding-map';
import { OpportunityList } from '@/components/jobhunt/opportunity-list';

export default function MissionControl() {
  const [items, setItems] = useState<MapItem[]>([]);
  const [excludeIds, setExcludeIds] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filteredIds, setFilteredIds] = useState<Set<string> | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchItems = useCallback(async (exclude?: Set<string>) => {
    setLoading(true);
    try {
      let url = '/api/jobhunt/embedding-map';
      if (exclude && exclude.size > 0) {
        url += '?exclude=' + Array.from(exclude).join(',');
      }
      let res = await fetch(url);
      // Fall back to static pre-computed file if API fails (e.g., no Qdrant)
      if (!res.ok) {
        res = await fetch('/embedding-map.json');
      }
      if (!res.ok) throw new Error('Failed to fetch embedding map');
      const data = await res.json();
      setItems(data.items || []);
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  // visibleIds: not excluded AND passes list filters (if any active)
  const visibleIds = new Set(
    items
      .filter(item => !excludeIds.has(item.id))
      .filter(item => !filteredIds || filteredIds.has(item.id))
      .map(item => item.id)
  );
  const visibleItems = items.filter(item => visibleIds.has(item.id));

  // Status counts
  const statusCounts: Record<string, number> = {};
  visibleItems.forEach(item => {
    statusCounts[item.status] = (statusCounts[item.status] || 0) + 1;
  });

  const handleMapSelect = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const handleListSelect = useCallback((id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  }, []);

  const handleFilterChange = useCallback((ids: Set<string>) => {
    // If the filter set matches all non-excluded items, treat as "no filter"
    const allNonExcluded = items.filter(i => !excludeIds.has(i.id));
    if (ids.size === allNonExcluded.length) {
      setFilteredIds(null);
    } else {
      setFilteredIds(ids);
    }
    setSelectedIds(new Set()); // clear selection when filter changes
  }, [items, excludeIds]);

  const handleReset = useCallback(() => {
    setExcludeIds(new Set());
    setSelectedIds(new Set());
    // Don't clear filteredIds — let the list's toggle state remain active
    // The list will re-notify via onFilterChange after items reload
    fetchItems();
  }, [fetchItems]);

  const handleSelect = useCallback(() => {
    // Keep only selected items visible: exclude everything NOT in selectedIds
    const allIds = new Set(items.map(i => i.id));
    const newExclude = new Set<string>();
    allIds.forEach(id => {
      if (!selectedIds.has(id)) newExclude.add(id);
    });
    setExcludeIds(newExclude);
    setSelectedIds(new Set());
    fetchItems(newExclude);
  }, [items, selectedIds, fetchItems]);

  const handlePrune = useCallback(() => {
    // Add selected items to exclude set
    const newExclude = new Set(excludeIds);
    selectedIds.forEach(id => newExclude.add(id));
    setExcludeIds(newExclude);
    setSelectedIds(new Set());
    fetchItems(newExclude);
  }, [excludeIds, selectedIds, fetchItems]);

  const statusSummary = Object.entries(statusCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([status, count]) => `${count} ${status}`)
    .join(' / ');

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: '#070d1c',
      display: 'flex',
      flexDirection: 'row',
      fontFamily: "'DM Sans', sans-serif",
      overflow: 'hidden',
    }}>
      {/* Left panel: Map */}
      <div style={{
        width: '60%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 16px 12px 16px',
        boxSizing: 'border-box',
      }}>
        {/* Header */}
        <div style={{ marginBottom: '8px' }}>
          <h1 style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: '24px',
            color: '#c8dde8',
            margin: 0,
            lineHeight: 1.2,
          }}>
            Mission Control
          </h1>
          <div style={{
            fontSize: '12px',
            color: '#5e7387',
            marginTop: '4px',
          }}>
            {visibleItems.length} items{statusSummary ? ` \u2014 ${statusSummary}` : ''}
          </div>
        </div>

        {/* Map area */}
        <div style={{
          flex: 1,
          minHeight: 0,
          borderRadius: '6px',
          border: '1px solid rgba(94, 115, 135, 0.2)',
          overflow: 'hidden',
        }}>
          {loading ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#5e7387',
              fontSize: '13px',
            }}>
              Loading...
            </div>
          ) : (
            <EmbeddingMap
              items={visibleItems}
              selectedIds={selectedIds}
              onSelect={handleMapSelect}
            />
          )}
        </div>

        {/* Button bar */}
        <div style={{
          display: 'flex',
          gap: '8px',
          marginTop: '10px',
        }}>
          <button
            onClick={handleReset}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              color: '#8ba4b8',
              backgroundColor: 'transparent',
              border: '1px solid rgba(139, 164, 184, 0.3)',
              borderRadius: '4px',
              padding: '5px 14px',
              cursor: 'pointer',
              letterSpacing: '0.5px',
              transition: 'border-color 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#8ba4b8';
              e.currentTarget.style.color = '#c8dde8';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(139, 164, 184, 0.3)';
              e.currentTarget.style.color = '#8ba4b8';
            }}
          >
            Reset
          </button>
          <button
            onClick={handleSelect}
            disabled={selectedIds.size === 0}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              color: selectedIds.size > 0 ? '#b8c84a' : '#5e7387',
              backgroundColor: 'transparent',
              border: `1px solid ${selectedIds.size > 0 ? 'rgba(184, 200, 74, 0.4)' : 'rgba(94, 115, 135, 0.2)'}`,
              borderRadius: '4px',
              padding: '5px 14px',
              cursor: selectedIds.size > 0 ? 'pointer' : 'default',
              letterSpacing: '0.5px',
              transition: 'border-color 0.15s, color 0.15s',
              opacity: selectedIds.size > 0 ? 1 : 0.5,
            }}
            onMouseEnter={(e) => {
              if (selectedIds.size > 0) {
                e.currentTarget.style.borderColor = '#b8c84a';
                e.currentTarget.style.color = '#d4e066';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedIds.size > 0) {
                e.currentTarget.style.borderColor = 'rgba(184, 200, 74, 0.4)';
                e.currentTarget.style.color = '#b8c84a';
              }
            }}
          >
            Select ({selectedIds.size})
          </button>
          <button
            onClick={handlePrune}
            disabled={selectedIds.size === 0}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              color: selectedIds.size > 0 ? '#e05555' : '#5e7387',
              backgroundColor: 'transparent',
              border: `1px solid ${selectedIds.size > 0 ? 'rgba(224, 85, 85, 0.4)' : 'rgba(94, 115, 135, 0.2)'}`,
              borderRadius: '4px',
              padding: '5px 14px',
              cursor: selectedIds.size > 0 ? 'pointer' : 'default',
              letterSpacing: '0.5px',
              transition: 'border-color 0.15s, color 0.15s',
              opacity: selectedIds.size > 0 ? 1 : 0.5,
            }}
            onMouseEnter={(e) => {
              if (selectedIds.size > 0) {
                e.currentTarget.style.borderColor = '#e05555';
                e.currentTarget.style.color = '#f07070';
              }
            }}
            onMouseLeave={(e) => {
              if (selectedIds.size > 0) {
                e.currentTarget.style.borderColor = 'rgba(224, 85, 85, 0.4)';
                e.currentTarget.style.color = '#e05555';
              }
            }}
          >
            Prune ({selectedIds.size})
          </button>
        </div>
      </div>

      {/* Right panel: List */}
      <div style={{
        width: '40%',
        height: '100%',
        borderLeft: '1px solid rgba(94, 115, 135, 0.2)',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          padding: '16px 12px 8px 12px',
          borderBottom: '1px solid rgba(94, 115, 135, 0.2)',
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            color: '#5e7387',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}>
            Opportunities ({visibleItems.length})
          </span>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <OpportunityList
            items={items}
            visibleIds={new Set(items.filter(i => !excludeIds.has(i.id)).map(i => i.id))}
            selectedId={expandedId}
            onSelect={handleListSelect}
            onFilterChange={handleFilterChange}
          />
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useRef, useState } from 'react';
import type { Mechanism } from './mechanism-card';

interface CausalGraphProps {
  mechanisms: Mechanism[];
  onSelectMechanism: (id: string) => void;
  selectedId?: string;
}

function buildMermaidDiagram(mechanisms: Mechanism[]): string {
  const lines: string[] = [
    'flowchart LR',
    '  classDef mech fill:#1e3a5f,stroke:#3b82f6,color:#93c5fd,rx:6',
    '  classDef pheno fill:#3d2e08,stroke:#d97706,color:#fcd34d,rx:12',
  ];

  // Assign safe node IDs
  const mechIds: Record<string, string> = {};
  mechanisms.forEach((m, i) => {
    mechIds[m.name || m.id] = `M${i}`;
  });

  // Collect phenotype targets (downstream_targets not in mechIds)
  const phenoTargets: Record<string, string> = {};
  let phenoIdx = 0;
  mechanisms.forEach((m) => {
    (m.downstream_targets ?? []).forEach(({ target_name }) => {
      if (!mechIds[target_name] && !phenoTargets[target_name]) {
        phenoTargets[target_name] = `P${phenoIdx++}`;
      }
    });
  });

  // Mechanism nodes
  mechanisms.forEach((m, i) => {
    const label = (m.name || m.description || m.id).replace(/"/g, "'").slice(0, 50);
    lines.push(`  M${i}["${label}"]:::mech`);
  });

  // Phenotype nodes
  Object.entries(phenoTargets).forEach(([name, nodeId]) => {
    const label = name.replace(/"/g, "'").slice(0, 50);
    lines.push(`  ${nodeId}(["${label}"]):::pheno`);
  });

  // Edges from downstream_targets
  mechanisms.forEach((m) => {
    const srcId = mechIds[m.name || m.id];
    (m.downstream_targets ?? []).forEach(({ target_name }) => {
      const dstId = mechIds[target_name] ?? phenoTargets[target_name];
      if (srcId && dstId) {
        lines.push(`  ${srcId} --> ${dstId}`);
      }
    });
  });

  return lines.join('\n');
}

export default function CausalGraph({ mechanisms, onSelectMechanism, selectedId }: CausalGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mechanisms.length === 0 || !containerRef.current) return;

    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
        const diagram = buildMermaidDiagram(mechanisms);
        const id = `causal-graph-${Date.now()}`;
        const { svg } = await mermaid.render(id, diagram);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();

    return () => { cancelled = true; };
  }, [mechanisms]);

  if (mechanisms.length === 0) {
    return <p className="text-sm text-slate-500">No mechanisms to visualize.</p>;
  }

  if (error) {
    return <p className="text-xs text-red-400">Graph render failed: {error}</p>;
  }

  return (
    <div className="space-y-3">
      {/* Mermaid SVG */}
      <div
        ref={containerRef}
        className="rounded-lg border border-slate-700 bg-slate-900/60 p-3 overflow-x-auto min-h-24 flex items-center justify-center text-slate-500 text-xs"
      >
        Rendering causal graph...
      </div>

      {/* Clickable mechanism list below graph */}
      <div className="space-y-1">
        {mechanisms.map((m, i) => (
          <button
            key={m.id}
            onClick={() => onSelectMechanism(m.id)}
            className={`w-full text-left text-xs px-3 py-1.5 rounded border transition-all ${
              selectedId === m.id
                ? 'border-cyan-500 bg-cyan-500/10 text-cyan-300'
                : 'border-slate-700 hover:border-slate-500 text-slate-300'
            }`}
          >
            <span className="font-mono text-slate-500 mr-2">M{i + 1}</span>
            {m.name || m.description?.slice(0, 60) || m.id}
          </button>
        ))}
      </div>
    </div>
  );
}

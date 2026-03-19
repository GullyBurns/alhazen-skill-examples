'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, HelpCircle, Dna } from 'lucide-react';

interface GapItem {
  hpo_id?: string;
  label?: string;
  symbol?: string;
  name?: string;
  type?: string;
  id?: string;
}

interface GapsSummary {
  undrugged_count: number;
  unexplained_phenotype_count: number;
  orphan_gene_count: number;
}

interface GapsPanelProps {
  undrugged: GapItem[];
  unexplained: GapItem[];
  orphanGenes: GapItem[];
  summary: GapsSummary;
}

export function GapsPanel({ undrugged, unexplained, orphanGenes, summary }: GapsPanelProps) {
  const allClear = summary.undrugged_count === 0 && summary.orphan_gene_count === 0;

  return (
    <div className="space-y-6">
      {/* Summary row */}
      <div className="flex flex-wrap gap-3">
        <Badge
          variant="outline"
          className={summary.undrugged_count > 0
            ? 'bg-red-500/15 text-red-300 border-red-500/30'
            : 'bg-green-500/15 text-green-300 border-green-500/30'}
        >
          {summary.undrugged_count} undrugged mechanism{summary.undrugged_count !== 1 ? 's' : ''}
        </Badge>
        <Badge variant="outline" className="bg-yellow-500/15 text-yellow-300 border-yellow-500/30">
          {summary.unexplained_phenotype_count} unexplained phenotype{summary.unexplained_phenotype_count !== 1 ? 's' : ''}
        </Badge>
        <Badge
          variant="outline"
          className={summary.orphan_gene_count > 0
            ? 'bg-red-500/15 text-red-300 border-red-500/30'
            : 'bg-green-500/15 text-green-300 border-green-500/30'}
        >
          {summary.orphan_gene_count} orphan gene{summary.orphan_gene_count !== 1 ? 's' : ''}
        </Badge>
      </div>

      {allClear && (
        <p className="text-sm text-green-400">
          All causal genes are incorporated into mechanisms, and all mechanisms have at least one therapeutic strategy.
        </p>
      )}

      {/* Undrugged mechanisms */}
      {undrugged.length > 0 && (
        <Card className="border-red-500/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-red-300">
              <AlertCircle className="w-4 h-4" />
              Undrugged Mechanisms
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {undrugged.map((m, i) => (
              <div key={m.id ?? i} className="text-sm p-2 rounded bg-red-500/5 border border-red-500/20">
                <span className="font-mono text-xs text-red-300 mr-2">{m.type}</span>
                <span className="text-foreground/80">{m.name}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Orphan genes */}
      {orphanGenes.length > 0 && (
        <Card className="border-orange-500/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-orange-300">
              <Dna className="w-4 h-4" />
              Orphan Causal Genes
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {orphanGenes.map((g, i) => (
              <Badge key={g.id ?? i} variant="outline" className="font-mono border-orange-500/30 text-orange-300">
                {g.symbol ?? g.name}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Unexplained phenotypes */}
      {unexplained.length > 0 && (
        <Card className="border-yellow-500/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-yellow-300">
              <HelpCircle className="w-4 h-4" />
              Unexplained Phenotypes ({unexplained.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {unexplained.map((p, i) => (
                <div
                  key={p.hpo_id ?? i}
                  className="flex items-center gap-2 px-3 py-1.5 rounded bg-yellow-500/5 border border-yellow-500/20 text-sm"
                >
                  <span className="truncate text-foreground/80">{p.label}</span>
                  <code className="ml-auto text-xs text-muted-foreground shrink-0">{p.hpo_id}</code>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

'use client';

import { Badge } from '@/components/ui/badge';

export interface PhenomeTier {
  frequency_tier: string;
  count: number;
  phenotypes: { hpo_id: string; label: string; frequency: string }[];
}

interface PhenomeTableProps {
  phenome: PhenomeTier[];
  total: number;
}

const TIER_STYLES: Record<string, { badge: string; dot: string; label: string }> = {
  obligate:  { badge: 'bg-red-500/15 text-red-300 border-red-500/30',    dot: 'bg-red-400',    label: 'Obligate (100%)' },
  frequent:  { badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30', dot: 'bg-orange-400', label: 'Frequent (30–79%)' },
  occasional:{ badge: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30', dot: 'bg-yellow-400', label: 'Occasional (5–29%)' },
  unknown:   { badge: 'bg-slate-500/15 text-slate-400 border-slate-500/30',  dot: 'bg-slate-500',  label: 'Unknown frequency' },
};

export function PhenomeTable({ phenome, total }: PhenomeTableProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">{total} total phenotypes</p>
      {phenome.map((tier) => {
        const style = TIER_STYLES[tier.frequency_tier] ?? TIER_STYLES.unknown;
        return (
          <div key={tier.frequency_tier}>
            <div className="flex items-center gap-2 mb-3">
              <span className={`w-2 h-2 rounded-full ${style.dot}`} />
              <Badge variant="outline" className={`text-xs ${style.badge}`}>
                {style.label}
              </Badge>
              <span className="text-xs text-muted-foreground">{tier.count}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {tier.phenotypes.map((p) => (
                <div
                  key={p.hpo_id}
                  className="flex items-center gap-2 px-3 py-2 rounded-md bg-card border border-border/50 text-sm"
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${style.dot}`} />
                  <span className="truncate">{p.label}</span>
                  <code className="ml-auto text-xs text-muted-foreground shrink-0">{p.hpo_id}</code>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

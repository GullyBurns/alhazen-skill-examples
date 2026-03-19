'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dna, Activity, Pill, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

export interface Mechanism {
  id: string;
  type: string;
  level: string;
  name: string;
  description: string;
  evidence_strength: string | null;
  therapeutic_addressability: string | null;
  genes: { symbol: string; id: string }[];
  phenotypes_caused: { hpo_id: string; label: string }[];
  therapeutic_strategies: { id: string; approach: string; name: string }[];
}

const TYPE_STYLES: Record<string, string> = {
  haploinsufficiency:    'bg-blue-500/15 text-blue-300 border-blue-500/30',
  'LoF-total':           'bg-red-500/15 text-red-300 border-red-500/30',
  'LoF-partial':         'bg-orange-500/15 text-orange-300 border-orange-500/30',
  GoF:                   'bg-purple-500/15 text-purple-300 border-purple-500/30',
  'dominant-negative':   'bg-yellow-500/15 text-yellow-300 border-yellow-500/30',
  'toxic-aggregation':   'bg-rose-500/15 text-rose-300 border-rose-500/30',
  'pathway-dysregulation': 'bg-teal-500/15 text-teal-300 border-teal-500/30',
};

const LEVEL_STYLES: Record<string, string> = {
  molecular: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  cellular:  'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  tissue:    'bg-green-500/15 text-green-300 border-green-500/30',
  systemic:  'bg-amber-500/15 text-amber-300 border-amber-500/30',
};

const MODALITY_LABELS: Record<string, string> = {
  'gene-therapy':              'Gene Therapy',
  'enzyme-replacement':        'Enzyme Replacement',
  'small-molecule-chaperone':  'Small Molecule Chaperone',
  'antisense-oligonucleotide': 'ASO',
  'substrate-reduction':       'Substrate Reduction',
  'pathway-activation':        'Pathway Activation',
  symptomatic:                 'Symptomatic',
};

interface MechanismCardProps {
  mechanism: Mechanism;
  index: number;
}

export function MechanismCard({ mechanism, index }: MechanismCardProps) {
  const [expanded, setExpanded] = useState(true);

  const typeStyle = TYPE_STYLES[mechanism.type] ?? 'bg-muted text-muted-foreground border-border';
  const levelStyle = LEVEL_STYLES[mechanism.level] ?? 'bg-muted text-muted-foreground border-border';

  return (
    <Card className="border-border/60">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-muted-foreground">M{index + 1}</span>
            <Badge variant="outline" className={typeStyle}>
              {mechanism.type}
            </Badge>
            <Badge variant="outline" className={levelStyle}>
              {mechanism.level}
            </Badge>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-muted-foreground hover:text-primary transition-colors shrink-0"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-sm text-foreground/90 leading-relaxed mt-1">{mechanism.description}</p>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-4">
          {/* Genes */}
          {mechanism.genes.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                <Dna className="w-3.5 h-3.5" />
                Causal Gene{mechanism.genes.length > 1 ? 's' : ''}
              </div>
              <div className="flex flex-wrap gap-2">
                {mechanism.genes.map((g) => (
                  <Badge key={g.id} variant="secondary" className="font-mono text-xs">
                    {g.symbol}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Phenotypes */}
          {mechanism.phenotypes_caused.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                <Activity className="w-3.5 h-3.5" />
                Explains {mechanism.phenotypes_caused.length} phenotype{mechanism.phenotypes_caused.length > 1 ? 's' : ''}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {mechanism.phenotypes_caused.map((p) => (
                  <span
                    key={p.hpo_id}
                    className="text-xs px-2 py-0.5 rounded-full bg-muted border border-border/50 text-foreground/80"
                    title={p.hpo_id}
                  >
                    {p.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Strategies */}
          {mechanism.therapeutic_strategies.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                <Pill className="w-3.5 h-3.5" />
                Therapeutic {mechanism.therapeutic_strategies.length > 1 ? 'Strategies' : 'Strategy'}
              </div>
              <div className="space-y-1.5">
                {mechanism.therapeutic_strategies.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-start gap-2 text-xs p-2 rounded bg-muted/40 border border-border/30"
                  >
                    <Badge variant="outline" className="text-xs shrink-0 mt-0.5 border-teal-500/30 text-teal-400 bg-teal-500/10">
                      {MODALITY_LABELS[s.approach] ?? s.approach}
                    </Badge>
                    <p className="text-foreground/70 leading-relaxed">{s.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

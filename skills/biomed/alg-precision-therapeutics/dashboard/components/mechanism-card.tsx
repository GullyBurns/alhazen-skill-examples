'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dna, Activity, Pill, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import EvidenceChain from './evidence-chain';

export interface Mechanism {
  id: string;
  type: string;
  level: string;
  name: string;
  description: string;
  confidence_tier?: string | null;
  evidence_strength: string | null;
  therapeutic_addressability: string | null;
  genes: { symbol: string; id: string }[];
  phenotypes_caused: { hpo_id: string; label: string }[];
  therapeutic_strategies: { id: string; approach: string; name: string }[];
  gene_descriptors: { term: string; hgnc_id: string }[];
  locations: { term: string; uberon_id: string }[];
  cell_types: { term: string; cl_id: string }[];
  biological_processes: { term: string; go_id: string }[];
  downstream_targets: { target_name: string }[];
}

const TIER_STYLES: Record<string, string> = {
  ESTABLISHED:  'bg-green-900/60 text-green-300 border-green-700',
  PROVISIONAL:  'bg-amber-900/60 text-amber-300 border-amber-700',
  HYPOTHETICAL: 'bg-blue-900/60 text-blue-300 border-blue-700',
};

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
  const tier = mechanism.confidence_tier || 'HYPOTHETICAL';
  const tierStyle = TIER_STYLES[tier] ?? TIER_STYLES.HYPOTHETICAL;

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
            <Badge variant="outline" className={`text-xs border ${tierStyle}`}>
              {tier}
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
          {/* Descriptor tags */}
          {((mechanism.gene_descriptors?.length ?? 0) > 0 ||
            (mechanism.locations?.length ?? 0) > 0 ||
            (mechanism.cell_types?.length ?? 0) > 0 ||
            (mechanism.biological_processes?.length ?? 0) > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {mechanism.gene_descriptors?.map((d) => (
                <a
                  key={d.hgnc_id}
                  href={`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${d.hgnc_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2 py-0.5 rounded border bg-blue-500/15 border-blue-500/30 text-blue-300 hover:bg-blue-500/25 transition-colors"
                >
                  {d.term}
                </a>
              ))}
              {mechanism.cell_types?.map((d) => (
                <a
                  key={d.cl_id}
                  href={`https://www.ebi.ac.uk/ols4/ontologies/cl/terms?obo_id=${d.cl_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2 py-0.5 rounded border bg-pink-500/15 border-pink-500/30 text-pink-300 hover:bg-pink-500/25 transition-colors"
                >
                  {d.term}
                </a>
              ))}
              {mechanism.locations?.map((d) => (
                <a
                  key={d.uberon_id}
                  href={`https://www.ebi.ac.uk/ols4/ontologies/uberon/terms?obo_id=${d.uberon_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2 py-0.5 rounded border bg-indigo-500/15 border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/25 transition-colors"
                >
                  {d.term}
                </a>
              ))}
              {mechanism.biological_processes?.map((d) => (
                <a
                  key={d.go_id}
                  href={`https://www.ebi.ac.uk/ols4/ontologies/go/terms?obo_id=${d.go_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2 py-0.5 rounded border bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25 transition-colors"
                >
                  {d.term}
                </a>
              ))}
            </div>
          )}

          {/* Downstream targets */}
          {(mechanism.downstream_targets?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs text-muted-foreground mb-1">Downstream targets</p>
              <div className="flex flex-wrap gap-1.5">
                {mechanism.downstream_targets.map((t, i) => (
                  <span
                    key={i}
                    className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 border border-slate-600"
                  >
                    {t.target_name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence chain */}
          <EvidenceChain mechanismId={mechanism.id} />

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

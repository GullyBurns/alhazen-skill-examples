'use client';

import { useState, useEffect, use, useRef } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MechanismCard, Mechanism } from '@/components/alg-precision-therapeutics/mechanism-card';
import { GapsPanel } from '@/components/alg-precision-therapeutics/gaps-panel';
import dynamic from 'next/dynamic';
import EvidenceSearch from '@/components/alg-precision-therapeutics/evidence-search';

const CausalGraph = dynamic(
  () => import('@/components/alg-precision-therapeutics/causal-graph'),
  { ssr: false }
);

interface Gene {
  id: string;
  symbol: string;
  hgnc_id: string;
  association_type: string;
}

interface Disease {
  id: string;
  name: string;
  mondo_id: string;
  omim_id: string | null;
  orpha_id: string | null;
  inheritance_pattern: string | null;
  prevalence: string | null;
  age_of_onset: string | null;
  phenotype_count: number;
  causal_genes: Gene[];
  mechanisms: unknown[];
}

interface GapData {
  undrugged_mechanisms: { id: string; name: string; type: string }[];
  unexplained_phenotypes: { hpo_id: string; label: string }[];
  orphan_genes: { id: string; symbol: string }[];
  summary: { undrugged_count: number; unexplained_phenotype_count: number; orphan_gene_count: number };
}

interface Treatment {
  id: string;
  name: string;
  description: string;
  maxo_id: string;
}

function Section({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="mb-6 border border-slate-700 rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-800/70 hover:bg-slate-800 transition-colors text-left"
        onClick={() => setOpen(!open)}
      >
        <span className="text-sm font-semibold text-slate-200">{title}</span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>
      {open && <div className="px-4 py-4">{children}</div>}
    </section>
  );
}

export default function DiseaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mondoId = decodeURIComponent(id);

  const [disease, setDisease] = useState<Disease | null>(null);
  const [mechanisms, setMechanisms] = useState<Mechanism[]>([]);
  const [genes, setGenes] = useState<Gene[]>([]);
  const [gaps, setGaps] = useState<GapData | null>(null);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [loading, setLoading] = useState(true);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [gapsLoaded, setGapsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMechId, setSelectedMechId] = useState<string | undefined>(undefined);

  const mechDetailRef = useRef<HTMLDivElement>(null);

  async function fetchCore() {
    setLoading(true);
    setError(null);
    try {
      const qs = `?mondo_id=${encodeURIComponent(mondoId)}`;
      const [diseaseRes, mechRes, genesRes, treatmentsRes] = await Promise.all([
        fetch(`/api/alg-precision-therapeutics/disease${qs}`),
        fetch(`/api/alg-precision-therapeutics/mechanisms${qs}`),
        fetch(`/api/alg-precision-therapeutics/genes${qs}`),
        fetch(`/api/alg-precision-therapeutics/treatments${qs}`),
      ]);

      const [diseaseData, mechData, genesData, treatmentsData] = await Promise.all([
        diseaseRes.json(),
        mechRes.json(),
        genesRes.json(),
        treatmentsRes.json(),
      ]);

      setDisease(diseaseData.disease ?? null);
      setMechanisms(mechData.mechanisms ?? []);
      setGenes([...(genesData.causal_genes ?? []), ...(genesData.associated_genes ?? [])]);
      setTreatments(treatmentsData.treatments ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }

  async function fetchGaps() {
    if (gapsLoaded) return;
    setGapsLoading(true);
    try {
      const res = await fetch(
        `/api/alg-precision-therapeutics/gaps?mondo_id=${encodeURIComponent(mondoId)}`
      );
      const data = await res.json();
      setGaps(data);
      setGapsLoaded(true);
    } catch {
      // gaps are non-critical
    } finally {
      setGapsLoading(false);
    }
  }

  useEffect(() => {
    fetchCore();
  }, [mondoId]);

  const handleSelectMechanism = (mechId: string) => {
    setSelectedMechId(mechId === selectedMechId ? undefined : mechId);
    // Scroll to detail section after state update
    setTimeout(() => {
      mechDetailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
  };

  const omimUrl = disease?.omim_id ? `https://omim.org/entry/${disease.omim_id}` : null;

  const selectedMech = mechanisms.find((m) => m.id === selectedMechId);

  const statCards = [
    {
      label: 'Mechanisms',
      value: mechanisms.length,
      colorText: 'text-teal-400',
      colorBg: 'bg-teal-500/10',
      colorBorder: 'border-teal-500/20',
    },
    {
      label: 'Phenotypes',
      value: disease?.phenotype_count ?? 0,
      colorText: 'text-orange-400',
      colorBg: 'bg-orange-500/10',
      colorBorder: 'border-orange-500/20',
    },
    {
      label: 'Genes',
      value: genes.length,
      colorText: 'text-blue-400',
      colorBg: 'bg-blue-500/10',
      colorBorder: 'border-blue-500/20',
    },
    {
      label: 'Treatments',
      value: treatments.length,
      colorText: 'text-violet-400',
      colorBg: 'bg-violet-500/10',
      colorBorder: 'border-violet-500/20',
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link
                href="/apt"
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Investigations
              </Link>
              {disease && (
                <div>
                  <h1 className="text-xl font-bold capitalize">{disease.name}</h1>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <code className="text-xs text-teal-400">{disease.mondo_id}</code>
                    {disease.omim_id && omimUrl && (
                      <a
                        href={omimUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
                      >
                        OMIM:{disease.omim_id}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    {disease.inheritance_pattern && (
                      <Badge
                        variant="outline"
                        className="text-xs border-slate-500/30 text-slate-400"
                      >
                        {disease.inheritance_pattern}
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchCore}
              disabled={loading}
              className="border-border/50 hover:border-teal-500/50 hover:bg-teal-500/10"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-5xl">
        {error && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-lg mb-6">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Section 1: Disease Header — stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {statCards.map((stat) => (
                <div
                  key={stat.label}
                  className={`rounded-lg border ${stat.colorBorder} ${stat.colorBg} p-4`}
                >
                  <div className={`text-3xl font-bold tabular-nums ${stat.colorText}`}>
                    {stat.value}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Section 2: Mechanism Cascade */}
            <Section title={`Section 2 — Mechanism Cascade (${mechanisms.length})`}>
              <div className="lg:grid lg:grid-cols-2 lg:gap-6">
                {/* Left: causal graph */}
                <div>
                  {mechanisms.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      No mechanisms yet. Run sensemaking to add them.
                    </p>
                  ) : (
                    <CausalGraph
                      mechanisms={mechanisms}
                      onSelectMechanism={handleSelectMechanism}
                      selectedId={selectedMechId}
                    />
                  )}
                </div>

                {/* Right: selected mechanism card */}
                <div ref={mechDetailRef}>
                  {selectedMech ? (
                    <div>
                      <p className="text-xs text-slate-500 mb-2">
                        Selected mechanism detail
                      </p>
                      <MechanismCard
                        mechanism={selectedMech}
                        index={mechanisms.findIndex((m) => m.id === selectedMech.id)}
                      />
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full min-h-32 border border-dashed border-slate-700 rounded-lg">
                      <p className="text-sm text-slate-500">
                        Click a mechanism to see details
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </Section>

            {/* Section 3: Therapeutic Landscape */}
            <Section title={`Section 3 — Therapeutic Landscape`}>
              <div className="lg:grid lg:grid-cols-2 lg:gap-6">
                {/* Genes table */}
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                    Causal &amp; Associated Genes
                  </h3>
                  {genes.length === 0 ? (
                    <p className="text-sm text-slate-500">No genes ingested.</p>
                  ) : (
                    <div className="rounded-lg border border-border/50 overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/40">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground text-xs">
                              Symbol
                            </th>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground text-xs">
                              HGNC
                            </th>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground text-xs">
                              Association
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {genes.map((g) => (
                            <tr
                              key={g.id}
                              className="border-t border-border/30 hover:bg-muted/20"
                            >
                              <td className="px-3 py-2 font-mono font-semibold text-sm">
                                {g.symbol}
                              </td>
                              <td className="px-3 py-2 text-muted-foreground text-xs">
                                <a
                                  href={`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${g.hgnc_id}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-cyan-400 font-semibold underline underline-offset-2 hover:text-blue-400 transition-colors flex items-center gap-1"
                                >
                                  {g.hgnc_id}
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              </td>
                              <td className="px-3 py-2">
                                <Badge
                                  variant="outline"
                                  className={
                                    g.association_type === 'causal'
                                      ? 'border-red-500/30 text-red-300 bg-red-500/10 text-xs'
                                      : 'text-xs'
                                  }
                                >
                                  {g.association_type}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Therapeutic strategies summary */}
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                    Therapeutic Strategies
                  </h3>
                  {mechanisms.reduce((s, m) => s + m.therapeutic_strategies.length, 0) === 0 ? (
                    <p className="text-sm text-slate-500">No strategies recorded yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {mechanisms
                        .filter((m) => m.therapeutic_strategies.length > 0)
                        .map((m) =>
                          m.therapeutic_strategies.map((s) => (
                            <div
                              key={s.id}
                              className="flex items-start gap-2 text-xs p-2 rounded bg-muted/40 border border-border/30"
                            >
                              <Badge
                                variant="outline"
                                className="text-xs shrink-0 mt-0.5 border-teal-500/30 text-teal-400 bg-teal-500/10"
                              >
                                {s.approach}
                              </Badge>
                              <p className="text-foreground/70 leading-relaxed">{s.name}</p>
                            </div>
                          ))
                        )}
                    </div>
                  )}
                </div>
              </div>
            </Section>

            {/* Section 4: Treatments */}
            <Section title={`Section 4 — Treatments (${treatments.length})`}>
              {treatments.length === 0 ? (
                <p className="text-sm text-slate-500">No treatments recorded.</p>
              ) : (
                <div className="space-y-3">
                  {treatments.map((t) => (
                    <div key={t.id} className="border border-border/50 rounded-lg p-3 bg-muted/20">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="text-sm font-semibold text-foreground">{t.name}</span>
                        {t.maxo_id && (
                          <code className="text-xs text-amber-400">{t.maxo_id}</code>
                        )}
                      </div>
                      {t.description && (
                        <p className="text-xs text-muted-foreground leading-relaxed">{t.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Section>

            {/* Section 5: Literature Search */}
            <Section title="Section 5 — Literature Search">
              <EvidenceSearch mondoId={mondoId} />
            </Section>

            {/* Section 6: Gaps */}
            <Section
              title="Section 6 — Knowledge Gaps"
              defaultOpen={false}
            >
              {gapsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-5 h-5 animate-spin text-muted-foreground" />
                </div>
              ) : gaps ? (
                <GapsPanel
                  undrugged={gaps.undrugged_mechanisms}
                  unexplained={gaps.unexplained_phenotypes}
                  orphanGenes={gaps.orphan_genes}
                  summary={gaps.summary}
                />
              ) : (
                <div className="text-center py-4">
                  <p className="text-sm text-slate-500 mb-3">
                    Load gap analysis to identify undrugged mechanisms and unexplained phenotypes.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchGaps}
                    className="border-border/50 hover:border-amber-500/50 hover:bg-amber-500/10"
                  >
                    Load Gap Analysis
                  </Button>
                </div>
              )}
            </Section>
          </>
        )}
      </main>

      <footer className="border-t border-border/50 mt-12">
        <div className="container mx-auto px-4 py-4">
          <p className="text-xs text-muted-foreground text-center">
            Disease Mechanism Dashboard &bull; Powered by TypeDB + Next.js
          </p>
        </div>
      </footer>
    </div>
  );
}

'use client';
import { useState } from 'react';

interface ClaimNote {
  claim_id: string;
  support_type: string;
  evidence_source: string;
  snippet: string;
  extraction_content: string;
  paper_title: string;
  paper_id: string;
  pmid: string;
}

interface EvidenceChainProps {
  mechanismId: string;
}

export default function EvidenceChain({ mechanismId }: EvidenceChainProps) {
  const [evidence, setEvidence] = useState<ClaimNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const supportColor = (type: string) => {
    if (type === 'SUPPORTS') return 'bg-green-900 text-green-300 border-green-700';
    if (type === 'REFUTES') return 'bg-red-900 text-red-300 border-red-700';
    return 'bg-amber-900 text-amber-300 border-amber-700';
  };

  const loadEvidence = async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/alg-precision-therapeutics/evidence?mechanism_id=${encodeURIComponent(mechanismId)}`);
      const data = await res.json();
      setEvidence(data.evidence || []);
      setLoaded(true);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3">
      <button
        onClick={loadEvidence}
        className="text-xs text-cyan-400 hover:text-blue-400 underline"
      >
        {loading ? 'Loading evidence...' : loaded ? `${evidence.length} evidence item(s)` : 'Load evidence'}
      </button>
      {loaded && evidence.length > 0 && (
        <div className="mt-2 space-y-2">
          {evidence.map((item) => (
            <EvidenceItem key={item.claim_id} item={item} supportColor={supportColor} />
          ))}
        </div>
      )}
      {loaded && evidence.length === 0 && (
        <p className="text-xs text-slate-500 mt-1">No evidence yet. Use add-evidence CLI to add.</p>
      )}
    </div>
  );
}

function EvidenceItem({
  item,
  supportColor,
}: {
  item: ClaimNote;
  supportColor: (t: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-slate-700 rounded p-2 bg-slate-800">
      <div className="flex items-start gap-2">
        <span
          className={`text-xs px-1.5 py-0.5 rounded border font-mono shrink-0 ${supportColor(item.support_type)}`}
        >
          {item.support_type}
        </span>
        <span className="text-xs text-slate-400">{item.evidence_source}</span>
        <button
          onClick={() => setExpanded(!expanded)}
          className="ml-auto text-xs text-slate-500 hover:text-slate-300"
        >
          {expanded ? '▲' : '▼'}
        </button>
      </div>
      <p className="text-xs text-slate-300 mt-1 italic">&ldquo;{item.snippet}&rdquo;</p>
      {expanded && (
        <div className="mt-2 border-t border-slate-700 pt-2 space-y-1">
          <p className="text-xs text-slate-400">{item.extraction_content}</p>
          <p className="text-xs text-slate-500">
            Source:{' '}
            {item.pmid ? (
              <a
                href={`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/`}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 font-semibold underline underline-offset-2 hover:text-blue-400 transition-colors"
              >
                {item.paper_title || `PMID:${item.pmid}`}
              </a>
            ) : (
              <span className="text-slate-400">{item.paper_title || item.paper_id}</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

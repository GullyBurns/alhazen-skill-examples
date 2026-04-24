'use client';

export interface Mechanism {
  id: string;
  type: string;
  level: string;
  name?: string;
  description: string;
  confidence_tier?: string;
  evidence_strength?: string | null;
  therapeutic_addressability?: string | null;
  genes: { symbol: string; id: string }[];
  phenotypes_caused: { hpo_id: string; label: string }[];
  therapeutic_strategies: { id: string; approach: string; name: string }[];
}

interface CausalChainFlowProps {
  mechanisms: Mechanism[];
  onSelectMechanism: (id: string) => void;
  selectedId?: string;
}

const tierColor = (tier?: string) => {
  if (tier === 'ESTABLISHED') return 'border-green-600 bg-green-950';
  if (tier === 'PROVISIONAL') return 'border-amber-600 bg-amber-950';
  return 'border-blue-600 bg-blue-950';
};

const tierBadge = (tier?: string) => {
  if (tier === 'ESTABLISHED') return 'bg-green-900 text-green-300';
  if (tier === 'PROVISIONAL') return 'bg-amber-900 text-amber-300';
  return 'bg-blue-900 text-blue-300';
};

export default function CausalChainFlow({
  mechanisms,
  onSelectMechanism,
  selectedId,
}: CausalChainFlowProps) {
  if (mechanisms.length === 0) {
    return <p className="text-sm text-slate-500">No mechanisms recorded yet.</p>;
  }
  return (
    <div className="space-y-3">
      {mechanisms.map((mech, i) => (
        <div key={mech.id}>
          <button
            onClick={() => onSelectMechanism(mech.id)}
            className={`w-full text-left border-2 rounded-lg p-3 transition-all ${tierColor(mech.confidence_tier)} ${
              selectedId === mech.id
                ? 'ring-2 ring-cyan-400'
                : 'hover:ring-1 hover:ring-cyan-600'
            }`}
          >
            <div className="flex items-start gap-2 flex-wrap">
              <span
                className={`text-xs px-1.5 py-0.5 rounded font-mono shrink-0 ${tierBadge(mech.confidence_tier)}`}
              >
                {mech.confidence_tier || 'HYPOTHETICAL'}
              </span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono shrink-0">
                {mech.type}
              </span>
              <span className="text-xs text-slate-400 shrink-0">{mech.level}</span>
            </div>
            <p className="text-sm text-slate-200 mt-1">{mech.description || mech.id}</p>
          </button>
          {i < mechanisms.length - 1 && (
            <div className="flex justify-center my-1">
              <span className="text-slate-600 text-xs">down causes</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

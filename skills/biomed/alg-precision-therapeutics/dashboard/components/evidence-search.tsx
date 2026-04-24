'use client';
import { useState } from 'react';

interface SearchResult {
  layer: string;
  id: string;
  content_preview: string;
  paper_title?: string;
  pmid?: string;
  support_type?: string;
  mechanism_id?: string;
  score: number;
}

interface EvidenceSearchProps {
  mondoId: string;
}

export default function EvidenceSearch({ mondoId }: EvidenceSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(false);
    try {
      const res = await fetch(
        `/api/alg-precision-therapeutics/search?query=${encodeURIComponent(query)}&mondo_id=${encodeURIComponent(mondoId)}`
      );
      const data = await res.json();
      setResults(data.results || []);
      setSearched(true);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Search mechanisms, evidence, literature..."
          className="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
        />
        <button
          onClick={search}
          disabled={loading}
          className="px-4 py-2 bg-cyan-800 hover:bg-cyan-700 text-cyan-100 text-sm rounded disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      {searched && results.length === 0 && (
        <p className="text-sm text-slate-500 mt-2">No results found.</p>
      )}
      {results.length > 0 && (
        <div className="mt-3 space-y-2">
          {results.map((r, i) => (
            <div key={i} className="border border-slate-700 rounded p-2 bg-slate-800">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                    r.layer === 'note' ? 'bg-amber-900 text-amber-300' : 'bg-blue-900 text-blue-300'
                  }`}
                >
                  {r.layer.toUpperCase()}
                </span>
                {r.support_type && (
                  <span className="text-xs text-slate-400">{r.support_type}</span>
                )}
                <span className="text-xs text-slate-500 ml-auto">score: {r.score}</span>
              </div>
              <p className="text-xs text-slate-300">{r.content_preview}</p>
              {r.paper_title && (
                <p className="text-xs text-slate-500 mt-1">
                  {r.pmid ? (
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${r.pmid}/`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-400 font-semibold underline underline-offset-2 hover:text-blue-400 transition-colors"
                    >
                      {r.paper_title}
                    </a>
                  ) : (
                    r.paper_title
                  )}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

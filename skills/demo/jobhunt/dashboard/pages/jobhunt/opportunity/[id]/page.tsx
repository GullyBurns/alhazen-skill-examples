'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Dossier } from '@/components/jobhunt/dossier';
import { TOKENS } from '@/components/jobhunt/tokens';

const T = TOKENS;

export default function OpportunityDossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`/api/jobhunt/opportunity/${id}`);
        const json = await res.json();
        if (json.success) {
          setData(json);
        } else {
          setError(json.error || 'Failed to load opportunity');
        }
      } catch (e) {
        setError('Failed to fetch opportunity data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div style={{
        background: T.bg, color: T.fgDim, fontFamily: T.sans,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', fontSize: 14,
      }}>
        <RefreshCw className="animate-spin mr-2" size={16} />
        Loading dossier...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{
        background: T.bg, color: T.fg, fontFamily: T.sans,
        padding: 40, display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <Link
          href="/jobhunt"
          style={{ color: T.teal, fontSize: 13, fontFamily: T.mono, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <ArrowLeft size={14} /> Back to inbox
        </Link>
        <div style={{ color: T.rust, fontSize: 14 }}>
          {error || 'Opportunity not found'}
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: T.bg, minHeight: '100vh' }}>
      <div style={{
        padding: '12px 20px', borderBottom: `1px solid ${T.borderDim}`,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <Link
          href="/jobhunt"
          style={{ color: T.teal, fontSize: 12, fontFamily: T.mono, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <ArrowLeft size={12} /> inbox
        </Link>
        <span style={{ color: T.fgFaint, fontFamily: T.mono, fontSize: 11 }}>·</span>
        <span style={{ color: T.fgDim, fontFamily: T.mono, fontSize: 11 }}>{id}</span>
      </div>
      <Dossier data={data} />
    </div>
  );
}

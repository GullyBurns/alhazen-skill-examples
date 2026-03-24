'use client';

import { Badge } from '@/components/ui/badge';
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from 'recharts';

export interface PhenomeTier {
  frequency_tier: string;
  count: number;
  phenotypes: { hpo_id: string; label: string; frequency: string }[];
}

interface PhenomeTableProps {
  phenome: PhenomeTier[];
  total: number;
}

const TIER_STYLES: Record<string, { badge: string; dot: string; label: string; color: string }> = {
  obligate:   { badge: 'bg-red-500/15 text-red-300 border-red-500/30',       dot: 'bg-red-400',    label: 'Obligate (100%)',      color: '#f87171' },
  frequent:   { badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30', dot: 'bg-orange-400', label: 'Frequent (30-79%)',  color: '#fb923c' },
  occasional: { badge: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30', dot: 'bg-yellow-400', label: 'Occasional (5-29%)', color: '#facc15' },
  unknown:    { badge: 'bg-slate-500/15 text-slate-400 border-slate-500/30',  dot: 'bg-slate-500',  label: 'Unknown frequency',   color: '#64748b' },
};

export function PhenomeTable({ phenome, total }: PhenomeTableProps) {
  const chartData = phenome
    .filter(tier => tier.count > 0)
    .map(tier => ({
      name: TIER_STYLES[tier.frequency_tier]?.label ?? tier.frequency_tier,
      count: tier.count,
      color: TIER_STYLES[tier.frequency_tier]?.color ?? '#64748b',
    }));

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">{total} total phenotypes</p>

      {/* Frequency distribution chart */}
      {chartData.length > 0 && (
        <div className="rounded-lg border border-border/50 bg-card/30 p-4">
          <p className="text-xs font-medium text-muted-foreground mb-3">Frequency Distribution</p>
          <ResponsiveContainer width="100%" height={chartData.length * 38 + 8}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 0, right: 32, bottom: 0, left: 8 }}
            >
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                width={148}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(222.2 84% 4.9%)',
                  border: '1px solid hsl(217.2 32.6% 17.5%)',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#94a3b8' }}
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} fillOpacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tier-by-tier detail */}
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

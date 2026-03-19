'use client';

import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dna, ChevronRight, Calendar } from 'lucide-react';

export interface Investigation {
  id: string;
  name: string;
  mondo_id: string;
  status: string;
  created_at: string;
}

interface InvestigationsListProps {
  investigations: Investigation[];
}

export function InvestigationsList({ investigations }: InvestigationsListProps) {
  if (investigations.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <Dna className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p>No investigations yet.</p>
        <p className="text-sm mt-1">
          Run <code className="text-xs bg-muted px-1 py-0.5 rounded">init-investigation MONDO:XXXXXXX</code> to start one.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {investigations.map((inv) => {
        const mondoId = inv.mondo_id;
        const diseaseName = inv.name.replace('APT Investigation: ', '');
        const date = new Date(inv.created_at).toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', year: 'numeric',
        });

        return (
          <Link
            key={inv.id}
            href={`/apt/disease/${encodeURIComponent(mondoId)}`}
            className="block group"
          >
            <Card className="transition-all hover:border-teal-500/50 hover:-translate-y-0.5">
              <CardContent className="py-4 px-5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <Dna className="w-5 h-5 text-teal-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium truncate capitalize">{diseaseName}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <code className="text-xs text-muted-foreground">{mondoId}</code>
                        <span className="text-muted-foreground/40">·</span>
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Calendar className="w-3 h-3" />
                          {date}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge
                      variant="outline"
                      className="text-xs border-teal-500/30 text-teal-400 bg-teal-500/10"
                    >
                      {inv.status}
                    </Badge>
                    <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}

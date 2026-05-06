"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Heart,
  Activity,
  Moon,
  Footprints,
  Target,
  Calendar,
  AlertCircle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

interface Metric {
  type: string;
  date: string;
  value: number;
  units: string;
}

interface Trend {
  metric_type: string;
  latest_value: number;
  avg_7d: number;
  delta_7d: number;
  direction: string;
}

interface Goal {
  id: string;
  name: string;
  metric: string;
  target: number;
  direction: string;
  status: string;
}

interface Appointment {
  id: string;
  name: string;
  type: string;
  date: string;
  status: string;
  provider: string | null;
}

interface Recommendation {
  id: string;
  name: string;
  content: string;
  priority: string;
  status: string;
}

interface PipelineStatus {
  last_ingest_date: string | null;
  records_count: number | null;
  health: string | null;
}

const METRIC_ICONS: Record<string, typeof Heart> = {
  heart_rate: Heart,
  step_count: Footprints,
  active_energy: Activity,
};

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "improving") return <TrendingUp className="w-4 h-4 text-green-400" />;
  if (direction === "regressing") return <TrendingDown className="w-4 h-4 text-red-400" />;
  return <Minus className="w-4 h-4 text-[#8ba4b8]" />;
}

function PipelineBadge({ health }: { health: string | null }) {
  const color = health === "healthy" ? "bg-green-500/20 text-green-400" :
    health === "stale" ? "bg-amber-500/20 text-amber-400" :
      "bg-red-500/20 text-red-400";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {health || "unknown"}
    </span>
  );
}

export default function CoachPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/coach/trends").then((r) => r.json()),
      fetch("/api/coach/goals").then((r) => r.json()),
      fetch("/api/coach/appointments").then((r) => r.json()),
      fetch("/api/coach/recommendations").then((r) => r.json()),
      fetch("/api/coach/pipeline").then((r) => r.json()),
    ]).then(([trendsData, goalsData, apptsData, recsData, pipeData]) => {
      setTrends(trendsData.trends || []);
      setGoals(goalsData.goals || []);
      setAppointments(apptsData.appointments || []);
      setRecommendations(recsData.recommendations || []);
      setPipeline(pipeData.pipeline || null);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse text-[#8ba4b8]">Loading health data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-[#5aadaf] to-[#4a7ab5] bg-clip-text text-transparent">
          Health Coach
        </h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[#8ba4b8]">Pipeline:</span>
          <PipelineBadge health={pipeline?.health || null} />
        </div>
      </div>

      {/* Metric Cards */}
      <section>
        <h2 className="text-lg font-semibold text-[#c8dde8] mb-3">Key Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {trends.map((t) => {
            const Icon = METRIC_ICONS[t.metric_type] || Activity;
            return (
              <div
                key={t.metric_type}
                className="rounded-lg border border-[#3d5c8f]/50 bg-[#0c1628] p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <Icon className="w-5 h-5 text-[#5aadaf]" />
                  <TrendIcon direction={t.direction} />
                </div>
                <div className="text-2xl font-bold text-[#c8dde8]">
                  {t.latest_value.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                </div>
                <div className="text-sm text-[#8ba4b8]">
                  {t.metric_type.replace(/_/g, " ")}
                </div>
                <div className="text-xs text-[#8ba4b8] mt-1">
                  7d avg: {t.avg_7d.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  {" "}({t.delta_7d >= 0 ? "+" : ""}{t.delta_7d.toFixed(1)})
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Goals */}
      {goals.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-[#c8dde8] mb-3 flex items-center gap-2">
            <Target className="w-5 h-5 text-[#b8c84a]" /> Active Goals
          </h2>
          <div className="space-y-2">
            {goals.map((g) => (
              <div
                key={g.id}
                className="flex items-center justify-between rounded-lg border border-[#3d5c8f]/30 bg-[#0c1628] px-4 py-3"
              >
                <div>
                  <span className="text-[#c8dde8] font-medium">{g.name}</span>
                  <span className="text-xs text-[#8ba4b8] ml-2">
                    {g.direction} {g.target} ({g.metric})
                  </span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-[#5aadaf]/20 text-[#5aadaf]">
                  {g.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-[#c8dde8] mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-[#b8c84a]" /> Recommendations
          </h2>
          <div className="space-y-2">
            {recommendations.map((r) => {
              const prioColor = r.priority === "high" ? "border-red-500/50" :
                r.priority === "medium" ? "border-[#b8c84a]/50" : "border-[#3d5c8f]/50";
              return (
                <div
                  key={r.id}
                  className={`rounded-lg border ${prioColor} bg-[#0c1628] px-4 py-3`}
                >
                  <div className="font-medium text-[#c8dde8]">{r.name}</div>
                  <div className="text-sm text-[#8ba4b8] mt-1">{r.content}</div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Upcoming Appointments */}
      {appointments.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-[#c8dde8] mb-3 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-[#5b8ab8]" /> Upcoming Appointments
          </h2>
          <div className="space-y-2">
            {appointments.filter(a => a.status === "upcoming").slice(0, 5).map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between rounded-lg border border-[#3d5c8f]/30 bg-[#0c1628] px-4 py-3"
              >
                <div>
                  <span className="text-[#c8dde8] font-medium">{a.name}</span>
                  {a.provider && (
                    <span className="text-xs text-[#8ba4b8] ml-2">with {a.provider}</span>
                  )}
                </div>
                <span className="text-sm text-[#8ba4b8]">
                  {new Date(a.date).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Navigation */}
      <nav className="flex gap-4 pt-4 border-t border-[#3d5c8f]/30">
        <Link href="/coach/trends" className="text-[#5aadaf] font-semibold underline underline-offset-2 hover:text-[#62c4bc] transition-colors">
          Trends
        </Link>
        <Link href="/coach/sleep" className="text-[#5aadaf] font-semibold underline underline-offset-2 hover:text-[#62c4bc] transition-colors">
          Sleep
        </Link>
        <Link href="/coach/workouts" className="text-[#5aadaf] font-semibold underline underline-offset-2 hover:text-[#62c4bc] transition-colors">
          Workouts
        </Link>
        <Link href="/coach/appointments" className="text-[#5aadaf] font-semibold underline underline-offset-2 hover:text-[#62c4bc] transition-colors">
          Appointments
        </Link>
      </nav>
    </div>
  );
}

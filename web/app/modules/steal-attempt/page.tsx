"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Info } from "lucide-react";
import Link from "next/link";
import LeaderboardTable from "@/components/LeaderboardTable";
import StatCard from "@/components/StatCard";
import DataFreshnessBanner from "@/components/DataFreshnessBanner";
import { stealAttemptModule } from "@/lib/modules/steal-attempt";

type View = "team" | "runner";

export default function StealAttemptPage() {
  const [view, setView] = useState<View>("team");
  const [teamData, setTeamData] = useState<Record<string, unknown>[]>([]);
  const [runnerData, setRunnerData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      const [t, r] = await Promise.all([
        fetch("/api/leaderboards/steal-team").then((res) => res.json()),
        fetch("/api/leaderboards/steal-runner").then((res) => res.json()),
      ]);
      setTeamData(t);
      setRunnerData(r);
      setLoading(false);
    }
    fetchAll();
  }, []);

  const rows = view === "team" ? teamData : runnerData;
  const columns = view === "team"
    ? stealAttemptModule.teamColumns
    : stealAttemptModule.coachColumns;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Live · 2020–2026</span>
          <DataFreshnessBanner />
        </div>
        <h1 className="text-3xl font-bold text-slate-900">{stealAttemptModule.name}</h1>
        <p className="text-slate-600 max-w-2xl leading-relaxed">{stealAttemptModule.description}</p>
      </div>

      {/* Key finding */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-700 leading-relaxed">
          <span className="font-semibold">Key finding:</span> {stealAttemptModule.headlineFinding}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="Most efficient team (full sample)"
          value="+3.25"
          sub="COL 2021 — 3.25 runs / 100 attempts"
          accent="green"
        />
        <StatCard
          label="Best individual runner"
          value="+3.74"
          sub="Myles Straw — 93 attempts"
          accent="green"
        />
        <StatCard
          label="Worst individual runner"
          value="-2.02"
          sub="Willy Adames — 52 attempts"
          accent="red"
        />
        <StatCard
          label="Overall good-steal rate"
          value="65.9%"
          sub="Attempts above break-even, 2020–2025"
          accent="blue"
        />
      </div>

      {/* Color key */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Good%:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
          &gt; 85% — elite decision-making
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block" />
          70–85% — average
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
          &lt; 70% — costly
        </span>
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg w-fit">
        {(["team", "runner"] as View[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
              view === v ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {v === "team" ? "By team-year" : "By runner"}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading…</div>
      ) : (
        <LeaderboardTable
          rows={rows}
          columns={columns}
          defaultSortKey="run_value_per100"
          defaultSortDir="desc"
        />
      )}

      {/* Methodology disclaimer */}
      <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium">About these grades</p>
          <p>
            Each steal attempt is graded against the RE24 break-even success rate for its
            base-out state. Empirical P(safe) comes from 27 bins (runner speed tier × catcher
            pop time tier × outs) computed from all graded attempts in 2020–2025.
            Pop time data is from Baseball Savant (2020+ only). Runners with fewer than 50
            career attempts are flagged <strong>Low</strong>. Double-steal contexts use the
            definitional pre-steal base state. 2020 entries are flagged <strong>60g</strong>.
            Entries marked <strong>Live</strong> are from the current in-progress season.{" "}
            <Link href="/methodology/steal-attempt" className="underline hover:text-amber-900">
              Full methodology
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

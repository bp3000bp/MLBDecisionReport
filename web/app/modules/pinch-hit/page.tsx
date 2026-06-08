"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Info } from "lucide-react";
import Link from "next/link";
import LeaderboardTable from "@/components/LeaderboardTable";
import StatCard from "@/components/StatCard";
import DataFreshnessBanner from "@/components/DataFreshnessBanner";
import { pinchHitModule } from "@/lib/modules/pinch-hit";

export default function PinchHitPage() {
  const [teamData, setTeamData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/leaderboards/pinch-hit-team")
      .then((res) => res.json())
      .then((data) => { setTeamData(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Live · 2020–2026</span>
          <DataFreshnessBanner />
        </div>
        <h1 className="text-3xl font-bold text-slate-900">{pinchHitModule.name}</h1>
        <p className="text-slate-600 max-w-2xl leading-relaxed">{pinchHitModule.description}</p>
      </div>

      {/* Key finding */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-700 leading-relaxed">
          <span className="font-semibold">Key finding:</span> {pinchHitModule.headlineFinding}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="PH appearances graded"
          value="23,946"
          sub="Across 210 team-seasons, 2020–2026"
          accent="blue"
        />
        <StatCard
          label="Good PH rate"
          value="64.5%"
          sub="Platoon upgrade vs. replaced batter"
          accent="blue"
        />
        <StatCard
          label="Avg run value / 100 PH"
          value="+3.1"
          sub="Expected runs added per 100 substitutions"
          accent="blue"
        />
        <StatCard
          label="2021 NL peak"
          value="+4.9"
          sub="RV/100 when NL still required pitchers to bat"
          accent="blue"
        />
      </div>

      {/* Color key */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Good%:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
          &gt; 70% — strong matchup discipline
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block" />
          50–70% — average
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
          &lt; 50% — majority of substitutions downgrade the matchup
        </span>
      </div>

      {/* Table */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-3">By team-year</h2>
        {loading ? (
          <div className="text-center py-16 text-slate-400">Loading…</div>
        ) : (
          <LeaderboardTable
            rows={teamData}
            columns={pinchHitModule.teamColumns}
            defaultSortKey="run_value_per100"
            defaultSortDir="desc"
          />
        )}
      </div>

      {/* Methodology disclaimer */}
      <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium">About these grades</p>
          <p>
            Each substitution is graded by comparing the pinch hitter&apos;s season wOBA
            vs. the pitcher&apos;s hand against the replaced batter&apos;s same split.
            Batters with fewer than 50 PA against a pitcher hand use the league-average
            split for that hand and season. Run value is leverage-weighted by the RE24
            value of the base-out state at substitution time, divided by the frequency-weighted
            mean RE across all MLB plate appearances (0.477). Entries marked{" "}
            <strong>Low</strong> have fewer than 20 PH appearances and carry higher
            uncertainty. 2020 entries are flagged <strong>60g</strong>. Entries marked{" "}
            <strong>Live</strong> are from the current in-progress season.
          </p>
        </div>
      </div>
    </div>
  );
}

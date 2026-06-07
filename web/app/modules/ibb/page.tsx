"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Info } from "lucide-react";
import Link from "next/link";
import LeaderboardTable from "@/components/LeaderboardTable";
import StatCard from "@/components/StatCard";
import DataFreshnessBanner from "@/components/DataFreshnessBanner";
import { ibbModule } from "@/lib/modules/ibb";

export default function IbbPage() {
  const [teamData, setTeamData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/leaderboards/ibb-team")
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
        <h1 className="text-3xl font-bold text-slate-900">{ibbModule.name}</h1>
        <p className="text-slate-600 max-w-2xl leading-relaxed">{ibbModule.description}</p>
      </div>

      {/* Key finding */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-700 leading-relaxed">
          <span className="font-semibold">Key finding:</span> {ibbModule.headlineFinding}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="IBBs graded (2020–2026)"
          value="3,124"
          sub="Across 209 team-seasons"
          accent="blue"
        />
        <StatCard
          label="Good IBB rate"
          value="2.5%"
          sub="Only 79 of 3,124 IBBs were value-positive"
          accent="red"
        />
        <StatCard
          label="Avg RE cost per IBB"
          value="+0.17"
          sub="Expected runs added to batting team"
          accent="blue"
        />
        <StatCard
          label="Avg run value per IBB"
          value="-0.14"
          sub="Net run cost to issuing team"
          accent="red"
        />
      </div>

      {/* Color key */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Good%:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
          &gt; 50% — majority of IBBs justified
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block" />
          30–50% — mixed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
          &lt; 30% — most IBBs not cost-effective
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
            columns={ibbModule.teamColumns}
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
            Each IBB is graded by comparing the matchup advantage gained
            (walked batter&apos;s wOBA vs. on-deck batter&apos;s wOBA, scaled by 1/wOBA_scale)
            against the RE24 run-expectancy cost of the intentional walk. Batter wOBA is
            computed from season Statcast data; batters with fewer than 50 PA use league
            average. Entries marked <strong>Low</strong> have fewer than 20 IBBs and carry
            higher uncertainty. 2020 entries are flagged <strong>60g</strong>.
            Entries marked <strong>Live</strong> are from the current in-progress season.{" "}
            <Link href="/methodology/ibb" className="underline hover:text-amber-900">
              Full methodology
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

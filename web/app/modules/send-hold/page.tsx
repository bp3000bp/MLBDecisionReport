"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Info } from "lucide-react";
import Link from "next/link";
import LeaderboardTable from "@/components/LeaderboardTable";
import StatCard from "@/components/StatCard";
import { sendHoldModule } from "@/lib/modules/send-hold";
import type { TeamRow, CoachRow } from "@/lib/modules/types";

type View = "team" | "coach";

export default function SendHoldPage() {
  const [view, setView] = useState<View>("team");
  const [teamData, setTeamData] = useState<TeamRow[]>([]);
  const [coachData, setCoachData] = useState<CoachRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      const [t, c] = await Promise.all([
        fetch("/api/leaderboards/team").then((r) => r.json()),
        fetch("/api/leaderboards/coach").then((r) => r.json()),
      ]);
      setTeamData(t);
      setCoachData(c);
      setLoading(false);
    }
    fetchAll();
  }, []);

  const rows = view === "team"
    ? (teamData as unknown as Record<string, unknown>[])
    : (coachData as unknown as Record<string, unknown>[]);
  const columns = view === "team" ? sendHoldModule.teamColumns : sendHoldModule.coachColumns;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Live · 2020–2024</span>
        </div>
        <h1 className="text-3xl font-bold text-slate-900">{sendHoldModule.name}</h1>
        <p className="text-slate-600 max-w-2xl leading-relaxed">{sendHoldModule.description}</p>
      </div>

      {/* Key finding */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-slate-700 leading-relaxed">
          <span className="font-semibold">Key finding:</span> {sendHoldModule.headlineFinding}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard
          label="Worst season (per 100)"
          value="11.97"
          sub="MIL 2020 — Ed Sedar (low sample)"
          accent="red"
        />
        <StatCard
          label="Worst (full sample)"
          value="9.42"
          sub="MIA 2023 — Griffin Benedict"
          accent="red"
        />
        <StatCard
          label="Best (full sample)"
          value="2.70"
          sub="ATL 2022 — Ron Washington"
          accent="green"
        />
        <StatCard
          label="Typical send rate"
          value="78–84%"
          sub="Middle-of-pack teams"
          accent="blue"
        />
      </div>

      {/* Color key */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Runs Left/100:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
          &lt; 4.5 — aggressive (good)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block" />
          4.5–7.0 — moderate
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />
          &gt; 7.0 — over-holding (costly)
        </span>
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg w-fit">
        {(["team", "coach"] as View[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
              view === v ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            {v === "team" ? "By team-year" : "Career totals"}
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
          defaultSortKey="bad_hold_runs_per100"
          defaultSortDir="desc"
        />
      )}

      {/* Methodology disclaimer */}
      <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium">About these grades</p>
          <p>
            Grades reflect expected run value at the moment of decision using empirical
            P(safe) from 18 situational bins (hit type × field position × outs) against
            RE24 break-even probabilities. P(safe) is estimated from season-average arm
            strength and sprint speed — play-level tracking is not available. Entries
            marked <strong>Low</strong> have fewer than 150 graded opportunities and carry
            higher uncertainty. 2020 entries are flagged <strong>60g</strong> (60-game season).{" "}
            <Link href="/methodology" className="underline hover:text-amber-900">
              Full methodology →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

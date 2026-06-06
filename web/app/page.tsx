import Link from "next/link";
import { ArrowRight, BarChart3, TrendingDown, AlertCircle, BookOpen } from "lucide-react";
import StatCard from "@/components/StatCard";
import { moduleRegistry } from "@/lib/modules/registry";

export default function Home() {
  const liveModules = moduleRegistry.filter((m) => m.status === "live");
  const comingSoon = moduleRegistry.filter((m) => m.status === "coming-soon");

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-center pt-8 pb-4 space-y-4">
        <div className="inline-flex items-center gap-2 text-sm text-blue-700 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
          <BarChart3 className="h-3.5 w-3.5" />
          <span>MLB 2020–2024 · 23,913 opportunities graded</span>
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 max-w-2xl mx-auto">
          Grading the decisions,<br className="hidden sm:block" /> not the players.
        </h1>
        <p className="text-lg text-slate-600 max-w-xl mx-auto">
          Run-expectancy grading of in-game baseball decisions — starting with
          third-base coach send/hold calls on extra-base opportunities.
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          {liveModules.map((m) => (
            <Link
              key={m.slug}
              href={`/modules/${m.slug}`}
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-blue-700 transition-colors"
            >
              {m.name}
              <ArrowRight className="h-4 w-4" />
            </Link>
          ))}
          <Link
            href="/methodology"
            className="inline-flex items-center gap-2 border border-slate-200 text-slate-700 px-5 py-2.5 rounded-xl font-medium hover:bg-white transition-colors"
          >
            <BookOpen className="h-4 w-4" />
            Methodology
          </Link>
        </div>
      </section>

      {/* Key finding banner */}
      <section className="bg-slate-900 text-white rounded-2xl p-6 sm:p-8">
        <div className="flex items-start gap-4 max-w-3xl mx-auto">
          <TrendingDown className="h-8 w-8 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h2 className="text-lg font-semibold text-white">Headline finding</h2>
            <p className="mt-1 text-slate-300 leading-relaxed">
              In every one of the 18 situational bins we analyzed — single or double,
              left/center/right field, 0–2 outs — the empirical probability of scoring
              exceeded the break-even threshold required to justify sending. Every run
              lost to baserunning decisions came from{" "}
              <span className="text-red-400 font-semibold">holding too often</span>,
              not from sending at the wrong time.
            </p>
            <p className="mt-3 text-slate-400 text-sm">
              The worst coaches left <span className="text-white">~9–12 runs per 100 opportunities</span> on
              the table. Over a full season (~180 opp), that&apos;s roughly{" "}
              <span className="text-white">16–22 runs</span> — more than 1.5 wins.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Opportunities graded" value="23,311" sub="2020–2024 regular season" accent="blue" />
        <StatCard label="Seasons covered" value="5" sub="2020 · 2021 · 2022 · 2023 · 2024" accent="blue" />
        <StatCard label="Coaches profiled" value="60" sub="≥1 season as 3B coach" accent="blue" />
        <StatCard label="External validation" value="+0.78" sub="Spearman ρ vs. BR XBT%" accent="green" />
      </section>

      {/* Module cards */}
      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-4">Decision modules</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {liveModules.map((m) => (
            <Link
              key={m.slug}
              href={`/modules/${m.slug}`}
              className="group bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <span className="inline-flex items-center text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Live</span>
                <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{m.name}</h3>
              <p className="mt-1 text-sm text-slate-600 leading-relaxed">{m.tagline}</p>
              <p className="mt-3 text-xs text-slate-400">{m.dateRange}</p>
            </Link>
          ))}

          {/* Coming soon placeholders */}
          {["Steal Attempt Grader", "IBB Decision Grader", "Pinch Hit Grader"].map((name) => (
            <div key={name} className="bg-white rounded-xl border border-slate-100 p-5 opacity-50">
              <span className="inline-flex items-center text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">Coming soon</span>
              <h3 className="mt-3 font-semibold text-slate-600">{name}</h3>
              <p className="mt-1 text-sm text-slate-400">In development</p>
            </div>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <section className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-medium">Scope and limitations</p>
          <p>
            This tool grades the <em>decision layer</em> only — whether a coach sent or held given
            what was knowable at the moment. It does not measure player ability, throw accuracy,
            relay execution, or other factors outside the coach&apos;s direct control. All P(safe)
            estimates use season-average statistics; play-level tracking data is not available.
            2020 entries reflect a 60-game season and carry higher uncertainty.{" "}
            <Link href="/methodology" className="underline hover:text-amber-900">Full methodology →</Link>
          </p>
        </div>
      </section>
    </div>
  );
}

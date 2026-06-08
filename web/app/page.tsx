import Link from "next/link";
import { ArrowRight, BarChart3, CheckCircle2, AlertCircle, BookOpen } from "lucide-react";
import StatCard from "@/components/StatCard";
import DataFreshnessBanner from "@/components/DataFreshnessBanner";
import { moduleRegistry } from "@/lib/modules/registry";

export default function Home() {
  const liveModules = moduleRegistry.filter((m) => m.status === "live");
  const comingSoonModules = moduleRegistry.filter((m) => m.status === "coming-soon");

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-center pt-8 pb-4 space-y-4">
        <div className="flex items-center justify-center gap-2 flex-wrap">
          <div className="inline-flex items-center gap-2 text-sm text-blue-700 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
            <BarChart3 className="h-3.5 w-3.5" />
            <span>MLB 2020–2026 · {liveModules.length} decision modules live</span>
          </div>
          <DataFreshnessBanner />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 max-w-2xl mx-auto">
          Grading the decisions,<br className="hidden sm:block" /> not the players.
        </h1>
        <p className="text-lg text-slate-600 max-w-xl mx-auto">
          Every in-game decision has a correct answer in expected-value terms. We find it,
          grade the actual call, and surface who&apos;s adding or costing their team runs —
          across every decision type we can measure.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
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

      {/* How it works */}
      <section className="bg-slate-900 text-white rounded-2xl p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-white mb-4">How it works</h2>
        <div className="grid sm:grid-cols-3 gap-6">
          <div className="space-y-2">
            <div className="text-blue-400 font-semibold text-sm uppercase tracking-wide">01 — Identify the decision</div>
            <p className="text-slate-300 text-sm leading-relaxed">
              Every baserunning opportunity, steal attempt, or tactical call is a discrete,
              time-stamped decision with a clear binary or categorical outcome.
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-blue-400 font-semibold text-sm uppercase tracking-wide">02 — Compute the break-even</div>
            <p className="text-slate-300 text-sm leading-relaxed">
              RE24 run-expectancy tables give us the exact success rate required to make a
              risky call worth it in expected-runs terms — before any outcome is known.
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-blue-400 font-semibold text-sm uppercase tracking-wide">03 — Grade the call</div>
            <p className="text-slate-300 text-sm leading-relaxed">
              We estimate the true probability of success using empirical binning on observable
              pre-play factors. Good decisions beat break-even; bad ones don&apos;t.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Decisions graded" value="~55K" sub="Across all live modules, 2020–2026" accent="blue" />
        <StatCard label="Seasons covered" value="7" sub="2020–2026 · 2026 in progress" accent="blue" />
        <StatCard label="Live modules" value={String(liveModules.length)} sub="Send/Hold · Steal · IBB" accent="blue" />
        <StatCard label="Spearman ρ" value="+0.78" sub="Send/Hold send rate vs. BR XBT%, n=120" accent="green" />
      </section>

      {/* Module cards */}
      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-1">Decision modules</h2>
        <p className="text-sm text-slate-500 mb-4">Each module grades a specific category of in-game call using the same expected-value framework.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {liveModules.map((m) => (
            <Link
              key={m.slug}
              href={`/modules/${m.slug}`}
              className="group bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <span className="inline-flex items-center gap-1 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">
                  <CheckCircle2 className="h-3 w-3" />
                  Live
                </span>
                <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{m.name}</h3>
              <p className="mt-1 text-sm text-slate-600 leading-relaxed">{m.tagline}</p>
              <p className="mt-3 text-xs text-slate-400">{m.dateRange}</p>
            </Link>
          ))}

          {/* Coming soon: from module registry */}
          {comingSoonModules.map((m) => (
            <div key={m.slug} className="bg-white rounded-xl border border-slate-100 p-5 opacity-60">
              <span className="inline-flex items-center text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium">In development</span>
              <h3 className="mt-3 font-semibold text-slate-700">{m.name}</h3>
              <p className="mt-1 text-sm text-slate-500 leading-relaxed">{m.tagline}</p>
            </div>
          ))}
          {/* Additional planned modules not yet in registry */}
          {["Starter Pull Timing Grader", "Bunt Decision Grader"].map((name) => (
            <div key={name} className="bg-white rounded-xl border border-slate-100 p-5 opacity-40">
              <span className="inline-flex items-center text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium">Planned</span>
              <h3 className="mt-3 font-semibold text-slate-600">{name}</h3>
              <p className="mt-1 text-sm text-slate-400">Scoped for a future release</p>
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
            This tool grades the <em>decision layer</em> only — whether a call was correct given
            what was knowable at the moment it was made. It does not measure player ability,
            execution quality, or factors outside the decision-maker&apos;s direct control.
            All probability estimates use empirical binning on season-average statistics;
            play-level tracking is not available for every input. 2020 entries reflect a
            60-game season and carry higher uncertainty.{" "}
            <Link href="/methodology" className="underline hover:text-amber-900">Full methodology →</Link>
          </p>
        </div>
      </section>
    </div>
  );
}

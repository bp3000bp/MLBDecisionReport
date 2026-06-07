import Link from "next/link";
import { ArrowLeft, ArrowRight, BookOpen } from "lucide-react";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-2">{title}</h2>
      <div className="text-slate-700 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

const modules = [
  {
    name: "Send/Hold Grader",
    slug: "send-hold",
    tagline: "Was the third-base coach's send or hold call correct by expected value?",
    status: "Live · 2020–2026",
  },
  {
    name: "Steal Attempt Grader",
    slug: "steal-attempt",
    tagline: "Was each stolen base attempt above the RE24 break-even success rate?",
    status: "Live · 2020–2026",
  },
  {
    name: "IBB Decision Grader",
    slug: "ibb",
    tagline: "Did the matchup gain from the intentional walk justify its run-expectancy cost?",
    status: "Live · 2020–2026",
  },
];

export default function MethodologyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <div className="space-y-2">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-3.5 w-3.5" /> Home
        </Link>
        <h1 className="text-3xl font-bold text-slate-900">Methodology</h1>
        <p className="text-slate-600">
          Every module is built on the same expected-value framework. Every shortcut is
          stated plainly. A clear limitation beats a suspiciously clean black box.
        </p>
      </div>

      <Section title="The shared framework">
        <p>
          Baseball Savant grades <em>player ability</em> — given a runner&apos;s tools,
          did he execute? We grade the <em>decision layer</em>: given what was knowable
          at the moment of the call, was the decision correct in expected-value terms?
        </p>
        <p>
          These are distinct questions. A talented runner sent on a 50/50 opportunity produces
          the same decision grade regardless of whether he happens to be safe or out. This is
          not a player evaluation tool.
        </p>
        <p>
          Every module follows the same three steps:
        </p>
        <ol className="list-decimal pl-5 space-y-2">
          <li>
            <strong>Identify the decision.</strong> Isolate plays where a discrete, attributable
            in-game call was made (send/hold, steal/no-steal, etc.) and the outcome is observable.
          </li>
          <li>
            <strong>Compute the break-even.</strong> Using a 24-state RE24 run-expectancy table
            built from 2020–2024 Statcast data, find the success probability at which the risky
            action produces equal expected run value to the conservative alternative:
            <pre className="bg-slate-100 rounded-lg p-3 text-sm font-mono overflow-x-auto mt-2">
              P_be = (RE_hold − RE_out) / (RE_safe − RE_out)
            </pre>
          </li>
          <li>
            <strong>Estimate P(success) and grade.</strong> We use an <em>empirical bin approach</em>:
            divide historical plays into bins defined by observable pre-play factors and compute the
            observed success rate within each bin. This avoids the selection bias of training a model
            only on cases where the risky action was attempted. Good decision = P(success) ≥ P_be.
          </li>
        </ol>
      </Section>

      <Section title="Run value">
        <p>
          Each graded decision carries a run value:
        </p>
        <pre className="bg-slate-100 rounded-lg p-3 text-sm font-mono overflow-x-auto">
          run_value = P(success) × RE_success + (1 − P(success)) × RE_failure − RE_hold
        </pre>
        <p>
          Positive run value = decision added expected runs relative to the alternative.
          Negative = runs left on the table (or needlessly risked). Leaderboards normalize
          this to <strong>run value per 100 decisions</strong> to account for differing
          opportunity counts.
        </p>
      </Section>

      {/* Per-module cards */}
      <section>
        <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-2 mb-4">
          Module-specific methodology
        </h2>
        <p className="text-slate-600 text-sm mb-5">
          Each module applies the shared framework to a specific decision type with its own
          data sources, bin structure, and known limitations.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {modules.map((m) => (
            <Link
              key={m.slug}
              href={`/methodology/${m.slug}`}
              className="group bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-blue-600" />
                  <span className="text-xs text-slate-500 font-medium">{m.status}</span>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{m.name}</h3>
              <p className="mt-1 text-sm text-slate-600 leading-relaxed">{m.tagline}</p>
            </Link>
          ))}
        </div>
      </section>

      <Section title="Common data sources">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Play-by-play (batting events):</strong> MLB Statcast via pybaseball (2020–2024).</li>
          <li><strong>Play-by-play (steal events):</strong> MLBAM Stats API (<code>/api/v1/game/&#123;game_pk&#125;/playByPlay</code>) — Statcast does not surface between-pitch steal events.</li>
          <li><strong>Runner sprint speed:</strong> Baseball Savant sprint speed leaderboard via pybaseball.</li>
          <li><strong>Catcher pop time:</strong> Baseball Savant pop time leaderboard CSV (2020+ only).</li>
          <li><strong>Outfielder arm strength:</strong> Baseball Savant arm strength leaderboard CSV (2020+ only — reason v1 is bounded to 2020–2024).</li>
          <li><strong>Run expectancy:</strong> 24-state RE24 table computed from 2020–2024 Statcast data.</li>
        </ul>
      </Section>

      <div className="pt-4 pb-8 flex gap-6">
        <Link href="/modules/send-hold" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
          ← Send/Hold Grader
        </Link>
        <Link href="/modules/steal-attempt" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
          ← Steal Attempt Grader
        </Link>
      </div>
    </div>
  );
}

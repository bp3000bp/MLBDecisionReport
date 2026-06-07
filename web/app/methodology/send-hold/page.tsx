import Link from "next/link";
import { ArrowLeft } from "lucide-react";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-2">{title}</h2>
      <div className="text-slate-700 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

function Limitation({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2">
      <span className="text-amber-500 mt-1">▲</span>
      <span>{children}</span>
    </li>
  );
}

export default function SendHoldMethodologyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <div className="space-y-2">
        <Link href="/methodology" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-3.5 w-3.5" /> Methodology overview
        </Link>
        <h1 className="text-3xl font-bold text-slate-900">Send/Hold Grader — Methodology</h1>
        <p className="text-slate-600">
          Detailed data sources, modeling choices, approximations, and known limitations
          for the third-base coach send/hold decision module.
        </p>
      </div>

      <Section title="What we measure">
        <p>
          For every ball hit to the outfield with a runner on second base, the third-base coach
          makes a binary call: send the runner to attempt to score, or hold him at third. We
          grade that call against the RE24 break-even probability for the situation.
        </p>
        <p>
          This is distinct from player ability. A talented runner sent on a 50/50 opportunity
          produces the same coach grade regardless of whether he happens to be safe or out.
        </p>
      </Section>

      <Section title="Scope">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Situation:</strong> Runner on second base, ball hit to the outfield (single or double), opportunity to attempt to score.</li>
          <li><strong>Years:</strong> 2020–2026 MLB regular season. 2026 is in progress; entries are flagged <strong>Live</strong> in the leaderboard.</li>
          <li><strong>Data source:</strong> MLB Statcast event-level data via pybaseball.</li>
          <li>Out of scope for this module: stolen bases, IBBs, other in-game decisions.</li>
        </ul>
      </Section>

      <Section title="Opportunity identification">
        <p>
          We filter Statcast play-by-play data for events where a runner was on second base
          (<code>on_2b</code> field) and the batter put the ball in play to the outfield
          (<code>hit_location</code> 7/8/9, <code>events</code> = single or double). We then
          parse the play description text (<code>des</code> field) to classify the runner&apos;s
          outcome: SCORED, OUT_AT_HOME, HELD_AT_BASE, or HELD_OR_UNKNOWN.
        </p>
        <p>
          To avoid false positives in multi-runner situations, outcomes are attributed to the
          specific runner on second using Unicode-normalized name matching against the description
          text. Plays classified as HELD_OR_UNKNOWN (~2.5% of opportunities) are excluded from grading.
        </p>
      </Section>

      <Section title="P(safe) — probability of scoring if sent">
        <p>
          We use an <strong>empirical bin approach</strong>: divide sent plays into 18 bins
          (2 event types × 3 field positions × 3 out states) and compute the fraction of sent
          runners who scored within each bin. This avoids the selection bias inherent in training
          a predictive model on sent plays only — coaches send more often when they expect success,
          so a model trained on sent plays would overstate P(safe) for holds.
        </p>
        <p>
          All 18 bins had empirical P(safe) ≥ 0.947 (range: 0.947–1.000). The minimum gap
          between empirical P(safe) and the maximum break-even probability across all bins was 0.033.
          This means sending was the statistically correct call in every bin — no bin produced a
          situation where holding was the right expected-value choice.
        </p>
        <p>
          A logistic regression model (AUC = 0.78, features: throw distance, runner sprint speed,
          outfielder arm strength, hit type, field position) is retained as a secondary comparison
          column, but is <em>not</em> used as the primary grading signal due to the selection bias
          issue described above.
        </p>
      </Section>

      <Section title="Throw distance approximation">
        <p>
          We do not have raw ball-tracking data. Throw distance is approximated from Statcast hit
          coordinates (<code>hc_x</code>, <code>hc_y</code>) using a scale factor of 2.5 feet per
          coordinate unit, calibrated against known field geometry. Spot checks: RF single ≈ 239 ft,
          LF single ≈ 180 ft, LF double ≈ 275 ft, RF double ≈ 268 ft — all plausible.
        </p>
        <p>
          This approximation affects the logistic regression model only. The empirical bin approach
          does not use throw distance.
        </p>
      </Section>

      <Section title="Break-even probability (RE24)">
        <p>
          The break-even probability is the P(safe) at which sending and holding produce equal
          expected run value:
        </p>
        <pre className="bg-slate-100 rounded-lg p-3 text-sm font-mono overflow-x-auto">
          P_be = (RE_hold − RE_out) / (RE_safe − RE_out)
        </pre>
        <p>
          RE values come from a 24-state run expectancy table computed from 2020–2024 Statcast data.
          State transitions account for other runners on base: the runner on 2B is assumed to score
          (RE_safe) or be retired (RE_out); the runner on 1B (if any) advances by one base on a
          single, two on a double.
        </p>
        <p>
          The runner on 3B (if any) is assumed to score on all outfield hits — this holds
          approximately 95% of the time and is a minor source of error.
        </p>
      </Section>

      <Section title="Grading logic">
        <p>
          Each play is graded using empirical P(safe) as the primary signal:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>GOOD_SEND:</strong> Runner was sent and empirical P(safe) ≥ P_be.</li>
          <li><strong>BAD_SEND:</strong> Runner was sent and empirical P(safe) &lt; P_be. (No plays in this category under the empirical approach — see key finding.)</li>
          <li><strong>BAD_HOLD:</strong> Runner was held and empirical P(safe) ≥ P_be. These represent run value left on the table.</li>
          <li><strong>GOOD_HOLD:</strong> Runner was held and empirical P(safe) &lt; P_be.</li>
        </ul>
        <p>
          Run value = P(safe) × RE_safe + (1 − P(safe)) × RE_out − RE_hold. Positive = correct
          decision. For BAD_HOLD plays this is the expected runs left on the table by the hold.
        </p>
      </Section>

      <Section title="Aggregation and leaderboards">
        <p>
          Team-year and coach-career leaderboards report <strong>bad_hold_runs_per100</strong>
          as the primary metric: the expected run value left on the table by over-holding,
          normalized per 100 opportunities. This accounts for variation in opportunity count
          across teams, seasons, and parks.
        </p>
        <p>
          Entries with fewer than 150 graded opportunities are flagged <strong>Low sample</strong>.
          The 2020 season (60 games) is separately flagged.
        </p>
      </Section>

      <Section title="External validation">
        <p>
          Send rate rankings were correlated against Baseball Reference&apos;s Extra Bases Taken %
          (XBT%) — the fraction of opportunities where a team took an extra base — as an independent
          external check. Spearman ρ = <strong>+0.780</strong> (p &lt; 0.0001, n = 120 team-years
          with ≥ 100 opportunities). Year-over-year stability of send_rate within our dataset:
          mean ρ = +0.340 (2022–23 pair: ρ = +0.436, p = 0.016).
        </p>
      </Section>

      <Section title="Data sources">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Play-by-play:</strong> MLB Statcast via pybaseball (<code>statcast()</code>, 2020–2024).</li>
          <li><strong>Sprint speed:</strong> Baseball Savant sprint speed leaderboard via pybaseball.</li>
          <li><strong>Arm strength:</strong> Baseball Savant arm strength leaderboard CSV (LF/CF/RF). Available 2020+ only.</li>
          <li><strong>Run expectancy:</strong> Computed from 2020–2024 Statcast data.</li>
          <li><strong>XBT%:</strong> Baseball Reference team baserunning pages.</li>
          <li><strong>Coach attribution:</strong> Baseball Reference team pages, manually compiled.</li>
        </ul>
      </Section>

      <Section title="Known limitations">
        <ul className="space-y-2">
          <Limitation>
            <strong>Throw distance is approximated</strong> from hit coordinates, not measured from
            tracking data. Scale factor 2.5 ft/unit is calibrated but not exact. Affects only the
            secondary logistic model.
          </Limitation>
          <Limitation>
            <strong>Arm strength is season-average</strong> by position for each outfielder. Play-level
            arm strength data is not publicly available.
          </Limitation>
          <Limitation>
            <strong>No relay-throw modeling.</strong> Cutoff and relay quality affects throw time to
            home, but this data is not in the public Statcast feed.
          </Limitation>
          <Limitation>
            <strong>Runner from 3B assumed to always score</strong> on outfield hits. True ~95% of the time.
          </Limitation>
          <Limitation>
            <strong>Runner from 1B advancement simplified:</strong> +1 base on a single, +2 bases on a double.
            Actual advancement varies.
          </Limitation>
          <Limitation>
            <strong>HELD_OR_UNKNOWN plays (~2.5%) excluded.</strong> The play description text did not
            unambiguously indicate the runner&apos;s outcome.
          </Limitation>
          <Limitation>
            <strong>2020 entries carry higher uncertainty</strong> due to the 60-game shortened season
            (~50–80 opportunities per team vs. ~150–220 in full seasons).
          </Limitation>
          <Limitation>
            <strong>Empirical P(safe) uses bin averages.</strong> Within-bin variation in throw distance,
            runner speed, and fielder arm is not captured. The empirical approach trades granularity
            for freedom from selection bias.
          </Limitation>
          <Limitation>
            <strong>Zero bad sends is a finding, not a gap.</strong> Under the empirical bin approach, no
            situation existed where sending was the wrong call at the bin level. This is stated plainly
            rather than forcing the model to produce bad sends to appear balanced.
          </Limitation>
        </ul>
      </Section>

      <div className="pt-4 pb-8 flex items-center justify-between">
        <Link href="/methodology" className="text-slate-500 hover:text-slate-700 text-sm font-medium inline-flex items-center gap-1.5">
          <ArrowLeft className="h-3.5 w-3.5" /> Methodology overview
        </Link>
        <Link href="/modules/send-hold" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
          View the Send/Hold Grader →
        </Link>
      </div>
    </div>
  );
}

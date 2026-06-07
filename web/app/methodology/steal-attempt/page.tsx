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

export default function StealAttemptMethodologyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <div className="space-y-2">
        <Link href="/methodology" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-3.5 w-3.5" /> Methodology overview
        </Link>
        <h1 className="text-3xl font-bold text-slate-900">Steal Attempt Grader — Methodology</h1>
        <p className="text-slate-600">
          Detailed data sources, modeling choices, approximations, and known limitations
          for the stolen base decision module.
        </p>
      </div>

      <Section title="What we measure">
        <p>
          Every stolen base attempt carries a break-even success rate — the threshold at which
          the attempt produces equal expected run value to not going. We estimate each runner&apos;s
          true probability of success given observable pre-play factors, compare it to the break-even,
          and grade the attempt accordingly.
        </p>
        <p>
          This grades the <em>decision</em> to attempt, not the execution. A fast runner who attempts
          against an elite catcher in a situation where the break-even is 80% and his estimated P(safe)
          is 70% receives a BAD_STEAL regardless of whether he happens to be safe.
        </p>
      </Section>

      <Section title="Scope">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Situations graded:</strong> Stolen base attempts of 2B and 3B only. Steal of home is excluded from v1 (rarer, more situationally complex, different decision-maker).</li>
          <li><strong>Includes:</strong> Successful steals, caught stealing, and pickoff-caught-stealing plays.</li>
          <li><strong>Years:</strong> 2020–2026 MLB regular season. 2026 is in progress; entries are flagged <strong>Live</strong> in the leaderboard.</li>
          <li><strong>Total graded (2020–2025):</strong> 16,526 attempts across 5 completed seasons.</li>
        </ul>
      </Section>

      <Section title="Data source — why not pybaseball?">
        <p>
          Steal events are <strong>not available in Baseball Savant&apos;s CSV export or
          pybaseball&apos;s <code>statcast()</code></strong>. That feed is pitch-level: each row
          represents a pitch. Stolen bases that happen between pitches — the runner breaks on a
          pitch, the ball is not put in play — do not appear as their own row. They show up only
          as a change in the base state between consecutive pitches, with no attributable play row.
        </p>
        <p>
          We use the <strong>MLBAM Stats API</strong> (<code>/api/v1/game/&#123;game_pk&#125;/playByPlay</code>)
          instead. This endpoint returns a structured play-by-play where steal events appear inside
          each at-bat&apos;s <code>runners</code> array with a <code>details.eventType</code> field
          (e.g., <code>stolen_base_2b</code>, <code>caught_stealing_3b</code>). We fetch all
          ~2,400 games per season concurrently using 15 parallel workers (~2 min/season).
        </p>
      </Section>

      <Section title="Merging steal events with Statcast context">
        <p>
          The MLBAM API provides the steal event and runner identity. We join each steal event
          to the corresponding Statcast at-bat (via <code>game_pk</code> and <code>at_bat_number</code>,
          where MLBAM&apos;s 0-based <code>atBatIndex + 1 = </code>statcast&apos;s 1-based
          <code> at_bat_number</code>) to obtain base-out state, catcher identity, and other context.
        </p>
      </Section>

      <Section title="Break-even probability — the double-steal problem">
        <p>
          RE24 break-even requires knowing the base-out state <em>before</em> the steal. Statcast
          records base state at the start of the at-bat, not at the moment of the steal mid-at-bat.
          For most plays this is fine — but double steals create a problem.
        </p>
        <p>
          When runners on 1B and 2B attempt to steal simultaneously, Statcast&apos;s at-bat-start
          state shows both bases occupied. The standard check &quot;is the target base empty?&quot;
          would incorrectly flag the steal of 2B as having <code>on_2b = 1</code> and return null
          break-even, dropping ~30% of steal-of-2B attempts.
        </p>
        <p>
          <strong>Fix — definitional pre-steal state:</strong> We assert the state the steal type
          requires by rule, regardless of what Statcast records for the at-bat start:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Steal of 2B → <code>on_1b = 1, on_2b = 0</code> (definitionally)</li>
          <li>Steal of 3B → <code>on_2b = 1, on_3b = 0</code> (definitionally)</li>
          <li>Uninvolved runners (e.g., <code>on_3b</code> for a steal-of-2B) are taken from Statcast as-is.</li>
        </ul>
        <p>
          After this fix, break-even coverage is 100% (16,526 / 16,526 graded attempts).
        </p>
      </Section>

      <Section title="P(safe) — empirical bin approach">
        <p>
          We use a <strong>27-bin empirical model</strong>: runner speed tier (fast/medium/slow)
          × catcher pop time tier (fast/medium/slow) × outs (0/1/2).
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Runner speed tier:</strong> Tertile split of Baseball Savant sprint speed (ft/s) by season. Fast = top third, slow = bottom third.</li>
          <li><strong>Catcher pop time tier:</strong> Tertile split of Baseball Savant pop time (2B SBA time for steal-of-2B; 3B SBA time for steal-of-3B). Fast = lowest pop time (best catcher), slow = highest.</li>
          <li><strong>Outs:</strong> 0, 1, or 2.</li>
        </ul>
        <p>
          Bins with fewer than 30 observations fall back to the outs-level marginal P(safe)
          across all speed/pop tiers. No bin is dropped entirely.
        </p>
        <p>
          Observed P(safe) ranges from <strong>0.694</strong> (slow runner vs. fast catcher) to
          <strong>0.860</strong> (fast runner vs. slow catcher). Overall success rate: 78.8%, consistent
          with the MLB new-rule era (2023+ runner placement rule inflates totals slightly).
        </p>
      </Section>

      <Section title="Catcher pop time — data and imputation">
        <p>
          Pop time data comes from the Baseball Savant pop time leaderboard CSV (2020+ only — a key
          reason the module is bounded to 2020–2024). Pop time is a season-level average per catcher,
          not a play-level measurement.
        </p>
        <p>
          For catchers with fewer than 10 steal opportunities in a given season (insufficient to
          establish a reliable pop time), we impute with the league-average pop time for that season.
          These entries are not separately flagged in the leaderboard because the imputation affects
          P(safe) at the individual-play level, not the aggregate.
        </p>
        <p>
          For successful steals (no caught-stealing), catcher identity comes from the Statcast
          <code> fielder_2</code> field. For caught-stealing plays, catcher identity comes from the
          MLBAM <code>credits</code> array (position code &quot;2&quot;). Credits take priority when both are available.
        </p>
      </Section>

      <Section title="Break-even probability (RE24)">
        <pre className="bg-slate-100 rounded-lg p-3 text-sm font-mono overflow-x-auto">
          P_be = (RE_hold − RE_out) / (RE_safe − RE_out)
        </pre>
        <p>
          RE states reflect the definitional pre-steal base state described above. For a steal of 2B,
          RE_hold uses the state with the runner on 1B; RE_safe uses the runner now on 2B; RE_out
          uses the runner retired with an out added. Uninvolved runners (e.g., a runner on 3B) are
          held constant across all three states.
        </p>
      </Section>

      <Section title="Grading logic">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>GOOD_STEAL:</strong> Empirical P(safe) ≥ P_be — the attempt was positive expected value.</li>
          <li><strong>BAD_STEAL:</strong> Empirical P(safe) &lt; P_be — the attempt was negative expected value.</li>
        </ul>
        <p>
          Run value = P(safe) × RE_safe + (1 − P(safe)) × RE_out − RE_hold. Positive = attempt
          added expected runs. Negative = attempt cost expected runs relative to not going.
        </p>
        <p>
          65.9% of all 2020–2024 steal attempts were GOOD_STEAL. Mean run value per attempt: +0.014
          (slight positive overall — the new-rule era has made stealing more viable on average).
        </p>
      </Section>

      <Section title="Aggregation and leaderboards">
        <p>
          The <strong>team-year leaderboard</strong> (150 team-seasons) reports run value per 100
          attempts as the primary metric. Entries with fewer than 50 attempts are flagged
          <strong> Low sample</strong>.
        </p>
        <p>
          The <strong>runner career leaderboard</strong> (820 runners with ≥ 1 attempt, 2020–2024)
          aggregates across all seasons. Runners with fewer than 50 career attempts are flagged
          <strong> Low sample</strong>. This module grades the runner&apos;s decision to go, not
          a coach or manager — the runner initiates the steal.
        </p>
      </Section>

      <Section title="Data sources">
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>Steal events:</strong> MLBAM Stats API play-by-play, fetched for all ~12,000 games (2020–2024).</li>
          <li><strong>Base-out state context:</strong> MLB Statcast via pybaseball, first pitch per at-bat.</li>
          <li><strong>Runner sprint speed:</strong> Baseball Savant sprint speed leaderboard via pybaseball.</li>
          <li><strong>Catcher pop time:</strong> Baseball Savant pop time leaderboard CSV (2020+ only).</li>
          <li><strong>Run expectancy:</strong> 24-state RE24 table computed from 2020–2024 Statcast data.</li>
        </ul>
      </Section>

      <Section title="Known limitations">
        <ul className="space-y-2">
          <Limitation>
            <strong>Runner speed and catcher pop time are season averages,</strong> not play-level
            measurements. In-season fatigue, injury, and handedness matchups are not captured.
          </Limitation>
          <Limitation>
            <strong>Pitcher delivery time is not modeled.</strong> A slow-to-the-plate lefty gives
            the runner a meaningful head start. This data is not in the public MLBAM feed at the
            play level.
          </Limitation>
          <Limitation>
            <strong>Steal of home is excluded.</strong> Home steals involve a fundamentally different
            decision-maker (the runner and/or manager) and situational complexity (pitcher windup,
            squeeze play). Excluded from v1.
          </Limitation>
          <Limitation>
            <strong>Double-steal base state uses the definitional approach.</strong> When two runners
            steal simultaneously, we assert the base state each steal requires by rule, which is
            correct for the primary runner but slightly approximates the true simultaneous-movement
            state for the partner runner.
          </Limitation>
          <Limitation>
            <strong>Pop time imputed for low-volume catchers.</strong> Catchers with fewer than 10
            steal attempts in a season use league-average pop time. This moderates the grading
            of attempts against backup catchers with thin samples.
          </Limitation>
          <Limitation>
            <strong>2020 entries carry higher uncertainty</strong> due to the 60-game shortened season.
          </Limitation>
          <Limitation>
            <strong>Empirical P(safe) uses bin averages.</strong> Within-bin variation (e.g., a
            &quot;fast&quot; runner at the top of the tier vs. the middle) is not captured. The
            empirical approach trades granularity for freedom from selection bias.
          </Limitation>
        </ul>
      </Section>

      <div className="pt-4 pb-8 flex items-center justify-between">
        <Link href="/methodology" className="text-slate-500 hover:text-slate-700 text-sm font-medium inline-flex items-center gap-1.5">
          <ArrowLeft className="h-3.5 w-3.5" /> Methodology overview
        </Link>
        <Link href="/modules/steal-attempt" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
          View the Steal Attempt Grader →
        </Link>
      </div>
    </div>
  );
}

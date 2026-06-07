import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-900 border-b border-slate-200 pb-2">{title}</h2>
      <div className="text-slate-700 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 font-mono text-sm text-slate-800">
      {children}
    </div>
  );
}

export default function IbbMethodologyPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-10">
      <div className="space-y-2">
        <Link href="/methodology" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-3.5 w-3.5" /> All methodology
        </Link>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">Live · 2020–2026</span>
          <span className="text-xs text-slate-500">2026 is in progress; entries are flagged Live</span>
        </div>
        <h1 className="text-3xl font-bold text-slate-900">IBB Decision Grader — Methodology</h1>
        <p className="text-slate-600">
          Grading intentional walk decisions by comparing the matchup gain against the
          run-expectancy cost of putting an additional runner on base.
        </p>
      </div>

      <Section title="What we are grading">
        <p>
          An intentional walk (IBB) is a deliberate, manager-called decision. The pitching
          team chooses to put the current batter on base — raising the batting team&apos;s
          run expectancy — in exchange for the right to face a (presumably) weaker on-deck hitter.
        </p>
        <p>
          We are grading the <em>decision</em>, not the players. The question is: at the
          moment the IBB was signaled, did the expected matchup improvement justify the
          run-expectancy cost?
        </p>
        <p>
          Note: this module grades from the <strong>fielding team&apos;s perspective</strong>
          — it is the pitching team (and their manager) whose decision we evaluate.
        </p>
      </Section>

      <Section title="Data source">
        <p>
          All inputs come from Statcast event-level data (2020–2026) via pybaseball.
          Intentional walks are identified by <code>events == &apos;intent_walk&apos;</code>.
          No external player-stats API is required — batter wOBA is computed directly from
          the <code>woba_value</code> and <code>woba_denom</code> Statcast fields present in
          the same parquets used by the rest of the pipeline.
        </p>
      </Section>

      <Section title="Run-expectancy cost of the IBB">
        <p>
          An IBB always increases the batting team&apos;s run expectancy (RE24). The cost
          is the difference in expected future runs between the post-IBB base-out state and
          the pre-IBB state, plus any run immediately forced in (bases-loaded IBB):
        </p>
        <Formula>
          re_cost = RE(post-IBB state, outs) - RE(pre-IBB state, outs) + runs_forced_in
        </Formula>
        <p>
          Post-IBB base state is deterministic: the batter goes to 1B; runners advance only
          if forced (runner on 1B is forced to 2B; runner on 2B is forced to 3B if 1B is also
          occupied; etc.). We use the same RE24 table (computed from Statcast 2020–2026) as
          the rest of the pipeline. re_cost is always non-negative.
        </p>
      </Section>

      <Section title="Batter and next-batter wOBA">
        <p>
          For each IBB, we compute the season wOBA for two players:
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>Batter wOBA:</strong> the player being intentionally walked.
            Computed from <code>sum(woba_value) / sum(woba_denom)</code> for that player
            in the same season, excluding IBBs (they have <code>woba_denom = 0</code>
            in Statcast — IBBs do not count toward the wOBA denominator).
          </li>
          <li>
            <strong>Next-batter wOBA:</strong> the player who came to bat immediately
            after the IBB in the same half-inning, identified from the Statcast
            at-bat sequence (<code>at_bat_number</code>). Their season wOBA is computed
            the same way.
          </li>
        </ul>
        <p>
          If either player has fewer than 50 PA in the season (small sample / early season),
          their wOBA is replaced with the league-average wOBA for that year.
          If there is no next batter in the half-inning (rare), league average is used.
        </p>
      </Section>

      <Section title="Grade formula">
        <p>
          The run value of the IBB decision (from the pitching team&apos;s perspective) is:
        </p>
        <Formula>
          matchup_adv = (batter_wOBA - next_batter_wOBA) / wOBA_scale<br />
          run_value   = matchup_adv - re_cost
        </Formula>
        <p>
          where <code>wOBA_scale = 1.157</code> (standard FanGraphs scaling factor that
          converts a wOBA difference to an expected run-per-PA difference).
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            <strong>GOOD_IBB (run_value &gt; 0):</strong> The matchup advantage exceeded
            the RE cost — the IBB saved expected runs on net.
          </li>
          <li>
            <strong>BAD_IBB (run_value ≤ 0):</strong> The RE cost exceeded the matchup
            gain — the IBB cost expected runs on net.
          </li>
        </ul>
      </Section>

      <Section title="Worked example">
        <p>
          Runner on 2B, 1 out. Elite batter (wOBA .390) at the plate. Weak hitter (.270 wOBA)
          on deck.
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>RE before IBB (runner on 2B, 1 out): ≈ 0.685 runs</li>
          <li>RE after IBB (runners on 1B + 2B, 1 out): ≈ 0.879 runs</li>
          <li>re_cost = 0.879 - 0.685 = 0.194</li>
          <li>matchup_adv = (.390 - .270) / 1.157 = 0.104</li>
          <li>run_value = 0.104 - 0.194 = <strong>-0.090</strong> → BAD_IBB</li>
        </ul>
        <p>
          Even walking a star to face a below-average hitter often fails to recover the RE
          cost of the IBB — a result consistent with the sabermetric consensus that IBBs
          are generally value-negative.
        </p>
      </Section>

      <Section title="Aggregation">
        <p>
          We aggregate by <strong>fielding team × season</strong> (the team that issued the IBBs):
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>n_ibb:</strong> total intentional walks issued</li>
          <li><strong>good_ibb_rate:</strong> fraction with run_value &gt; 0</li>
          <li><strong>avg_re_cost:</strong> mean RE cost per IBB</li>
          <li><strong>run_value_per100:</strong> total run_value / n_ibb × 100</li>
          <li><strong>total_run_value:</strong> sum of all run_value for the team-season</li>
        </ul>
        <p>
          Positive run_value_per100 means the team&apos;s IBBs added expected value on net.
          Negative means they subtracted expected value. Teams with fewer than 20 IBBs in a
          season are flagged <strong>Low</strong>.
        </p>
      </Section>

      <Section title="Limitations">
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong>Season-average wOBA:</strong> We use the full-season wOBA for both
            batters, not game-to-game splits, hot/cold streaks, or platoon matchups. A
            manager deciding on an IBB has access to much richer context — pitch type,
            recent performance, field positioning — that this model does not capture.
          </li>
          <li>
            <strong>No pitcher quality signal:</strong> We do not model the current pitcher&apos;s
            ability to handle either batter. An ace might be trusted to pitch around an elite
            batter; this model treats all pitchers as equivalent.
          </li>
          <li>
            <strong>Next-batter assumption:</strong> We assume the on-deck hitter actually
            bats next. Pinch-hit substitutions that follow an IBB would change the effective
            matchup; this model uses the player who appears next in the Statcast record.
          </li>
          <li>
            <strong>Small per-team sample:</strong> Post-2017 automatic IBB rule, teams
            issue 15–25 IBBs per season. Team-level estimates carry meaningful uncertainty.
            Career / multi-season trends are more reliable.
          </li>
          <li>
            <strong>Bases-loaded IBBs:</strong> When the bases are loaded, an IBB forces
            in a run. We add that run to re_cost. These situations are rare but occur; they
            are nearly always BAD_IBBs under any model.
          </li>
          <li>
            <strong>No manager attribution:</strong> We aggregate at the team-year level.
            Manager names require a separate managers lookup CSV not yet included in the
            automated pipeline.
          </li>
          <li>
            <strong>2020 short season:</strong> The 60-game 2020 season produces very small
            per-team IBB counts (often 5–15). These entries are flagged <strong>60g</strong>.
          </li>
        </ul>
      </Section>

      <Section title="Why most IBBs look suboptimal">
        <p>
          The sabermetric consensus — and our model — finds that most IBBs are value-negative.
          This is not a modeling artifact. The RE cost of adding a runner (typically 0.15–0.30
          runs depending on situation) requires the walked batter to be dramatically better
          than the on-deck hitter to break even. For an IBB with re_cost = 0.20:
        </p>
        <Formula>
          break-even wOBA gap = re_cost × wOBA_scale = 0.20 × 1.157 ≈ 0.23 wOBA points
        </Formula>
        <p>
          A gap of .230 wOBA points between the walked batter and the next hitter is
          enormous — roughly the difference between an average hitter (.320 wOBA) and a
          historically bad bat (.090). In practice, most IBBs involve a gap of .050–.120,
          far below the break-even threshold.
        </p>
        <p>
          This finding should be interpreted as context — our model quantifies how much
          teams historically paid for IBBs, not a directive to never use them. Late-game,
          bases-loaded, two-out situations introduce strategic considerations (forcing a
          double play, choosing reliever matchups) that are outside this model&apos;s scope.
        </p>
      </Section>

      <div className="flex items-center justify-between pt-4 border-t border-slate-200">
        <Link href="/methodology" className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" /> All methodology
        </Link>
        <Link href="/modules/ibb" className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 hover:text-blue-900">
          View leaderboard <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

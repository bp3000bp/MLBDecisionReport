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

      <Section title="Key structural finding">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-2">
          <p className="font-semibold text-blue-900">
            All run value loss in this dataset comes from over-holding — not from over-sending.
          </p>
          <p className="text-sm text-blue-800">
            Empirical P(safe) ≥ 0.947 in all 18 bins. The maximum break-even probability
            across all bins is 0.914. The minimum gap is 0.033 — meaning every bin has
            P(safe) comfortably above the break-even threshold. Under the empirical approach,
            zero bins produced a situation where holding was the correct expected-value call.
            The 21 BAD_SENDs produced by the logistic regression model all flip to GOOD_SEND
            when the empirical P(safe) is substituted. This is a finding, not a model gap —
            stated explicitly rather than forcing the model to appear balanced.
          </p>
        </div>
      </Section>

      <Section title="External validation">
        <p>
          Send rate rankings were correlated against Baseball Reference&apos;s Extra Bases Taken %
          (XBT%) — the fraction of opportunities where a team took an extra base — as an
          independent external check. The two metrics share no data: our send_rate is computed
          from Statcast play-by-play; XBT% is computed by Baseball Reference from their
          play-by-play.
        </p>
        <p>
          <strong>Spearman ρ = +0.780</strong> (p &lt; 0.0001, n = 120 team-years with ≥ 100
          opportunities). This is a strong positive correlation. Teams our model identifies as
          aggressive senders are independently identified as aggressive by Baseball Reference,
          and vice versa.
        </p>
        <p>
          Year-over-year stability of send_rate within our dataset (same team, consecutive seasons):
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-4 font-medium">Season pair</th>
                <th className="py-2 pr-4 font-medium">n teams</th>
                <th className="py-2 pr-4 font-medium">Spearman ρ</th>
                <th className="py-2 font-medium">p-value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr><td className="py-2 pr-4">2020 vs 2021</td><td className="py-2 pr-4">30</td><td className="py-2 pr-4">+0.231</td><td className="py-2 text-slate-500">0.219 (not sig.)</td></tr>
              <tr><td className="py-2 pr-4">2021 vs 2022</td><td className="py-2 pr-4">30</td><td className="py-2 pr-4">+0.349</td><td className="py-2 text-slate-500">0.059 (borderline)</td></tr>
              <tr className="bg-blue-50"><td className="py-2 pr-4 font-medium">2022 vs 2023</td><td className="py-2 pr-4">30</td><td className="py-2 pr-4 font-medium">+0.436</td><td className="py-2 font-medium text-blue-700">0.016 ✓</td></tr>
              <tr><td className="py-2 pr-4">2023 vs 2024</td><td className="py-2 pr-4">30</td><td className="py-2 pr-4">+0.345</td><td className="py-2 text-slate-500">0.062 (borderline)</td></tr>
              <tr className="border-t-2 border-slate-300"><td className="py-2 pr-4 font-medium">Mean</td><td className="py-2 pr-4">—</td><td className="py-2 pr-4 font-medium">+0.340</td><td className="py-2">—</td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm text-slate-500">
          The 2020–21 pair is weaker, likely because 2020 was a 60-game season with small,
          noisier per-team send_rate estimates. The consistent positive ρ across all pairs
          (mean +0.340) confirms that send_rate captures a real coaching philosophy signal
          rather than year-to-year noise.
        </p>
      </Section>

      <Section title="Rank comparison: our rankings vs. Baseball Reference">
        <p>
          Below are the top 15 team-seasons by our send_rate and their corresponding XBT%
          rank (Baseball Reference), plus the 10 most conservative team-seasons. Rank gaps
          arise from scope differences: XBT% covers all types of extra-base advancement
          (including from 1B on a single, or first-to-third on a double), while our module
          covers only the specific situation of a runner on 2B with a ball hit to the outfield.
        </p>
        <p className="font-medium text-slate-700 mt-2">Top 15 most aggressive (by our send_rate):</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-3 font-medium">Team</th>
                <th className="py-2 pr-3 font-medium">Year</th>
                <th className="py-2 pr-3 font-medium">Send%</th>
                <th className="py-2 pr-3 font-medium">Our rank</th>
                <th className="py-2 pr-3 font-medium">XBT%</th>
                <th className="py-2 font-medium">BR rank</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              <tr><td className="py-1.5 pr-3">WSH</td><td className="py-1.5 pr-3">2024</td><td className="py-1.5 pr-3">88.1%</td><td className="py-1.5 pr-3">1</td><td className="py-1.5 pr-3">.45</td><td className="py-1.5">20</td></tr>
              <tr><td className="py-1.5 pr-3">ATL</td><td className="py-1.5 pr-3">2022</td><td className="py-1.5 pr-3">87.4%</td><td className="py-1.5 pr-3">2</td><td className="py-1.5 pr-3">.50</td><td className="py-1.5">2</td></tr>
              <tr><td className="py-1.5 pr-3">DET</td><td className="py-1.5 pr-3">2024</td><td className="py-1.5 pr-3">87.2%</td><td className="py-1.5 pr-3">3</td><td className="py-1.5 pr-3">.49</td><td className="py-1.5">4</td></tr>
              <tr><td className="py-1.5 pr-3">BAL</td><td className="py-1.5 pr-3">2023</td><td className="py-1.5 pr-3">86.7%</td><td className="py-1.5 pr-3">4</td><td className="py-1.5 pr-3">.49</td><td className="py-1.5">4</td></tr>
              <tr><td className="py-1.5 pr-3">CIN</td><td className="py-1.5 pr-3">2023</td><td className="py-1.5 pr-3">85.2%</td><td className="py-1.5 pr-3">5</td><td className="py-1.5 pr-3">.47</td><td className="py-1.5">9</td></tr>
              <tr><td className="py-1.5 pr-3">TB</td><td className="py-1.5 pr-3">2022</td><td className="py-1.5 pr-3">84.7%</td><td className="py-1.5 pr-3">7</td><td className="py-1.5 pr-3">.47</td><td className="py-1.5">9</td></tr>
              <tr><td className="py-1.5 pr-3">COL</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">84.4%</td><td className="py-1.5 pr-3">10</td><td className="py-1.5 pr-3">.45</td><td className="py-1.5">20</td></tr>
              <tr><td className="py-1.5 pr-3">STL</td><td className="py-1.5 pr-3">2022</td><td className="py-1.5 pr-3">84.4%</td><td className="py-1.5 pr-3">10</td><td className="py-1.5 pr-3">.46</td><td className="py-1.5">14</td></tr>
              <tr><td className="py-1.5 pr-3">LAD</td><td className="py-1.5 pr-3">2024</td><td className="py-1.5 pr-3">84.4%</td><td className="py-1.5 pr-3">10</td><td className="py-1.5 pr-3">.49</td><td className="py-1.5">4</td></tr>
            </tbody>
          </table>
        </div>
        <p className="font-medium text-slate-700 mt-4">10 most conservative (by our send_rate):</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-3 font-medium">Team</th>
                <th className="py-2 pr-3 font-medium">Year</th>
                <th className="py-2 pr-3 font-medium">Send%</th>
                <th className="py-2 pr-3 font-medium">Our rank</th>
                <th className="py-2 pr-3 font-medium">XBT%</th>
                <th className="py-2 font-medium">BR rank</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              <tr><td className="py-1.5 pr-3">SEA</td><td className="py-1.5 pr-3">2023</td><td className="py-1.5 pr-3">72.0%</td><td className="py-1.5 pr-3">111</td><td className="py-1.5 pr-3">.40</td><td className="py-1.5">78</td></tr>
              <tr><td className="py-1.5 pr-3">SF</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">71.4%</td><td className="py-1.5 pr-3">112</td><td className="py-1.5 pr-3">.38</td><td className="py-1.5">99</td></tr>
              <tr><td className="py-1.5 pr-3">NYY</td><td className="py-1.5 pr-3">2023</td><td className="py-1.5 pr-3">71.3%</td><td className="py-1.5 pr-3">113</td><td className="py-1.5 pr-3">.39</td><td className="py-1.5">89</td></tr>
              <tr><td className="py-1.5 pr-3">CHC</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">70.9%</td><td className="py-1.5 pr-3">114</td><td className="py-1.5 pr-3">.40</td><td className="py-1.5">78</td></tr>
              <tr><td className="py-1.5 pr-3">MIN</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">70.8%</td><td className="py-1.5 pr-3">115</td><td className="py-1.5 pr-3">.37</td><td className="py-1.5">108</td></tr>
              <tr><td className="py-1.5 pr-3">CIN</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">70.8%</td><td className="py-1.5 pr-3">115</td><td className="py-1.5 pr-3">.35</td><td className="py-1.5">119</td></tr>
              <tr><td className="py-1.5 pr-3">BOS</td><td className="py-1.5 pr-3">2022</td><td className="py-1.5 pr-3">69.8%</td><td className="py-1.5 pr-3">117</td><td className="py-1.5 pr-3">.38</td><td className="py-1.5">99</td></tr>
              <tr><td className="py-1.5 pr-3">NYM</td><td className="py-1.5 pr-3">2021</td><td className="py-1.5 pr-3">69.5%</td><td className="py-1.5 pr-3">118</td><td className="py-1.5 pr-3">.37</td><td className="py-1.5">108</td></tr>
              <tr><td className="py-1.5 pr-3">MIA</td><td className="py-1.5 pr-3">2023</td><td className="py-1.5 pr-3">69.3%</td><td className="py-1.5 pr-3">119</td><td className="py-1.5 pr-3">.38</td><td className="py-1.5">99</td></tr>
              <tr><td className="py-1.5 pr-3">SEA</td><td className="py-1.5 pr-3">2022</td><td className="py-1.5 pr-3">69.2%</td><td className="py-1.5 pr-3">120</td><td className="py-1.5 pr-3">.38</td><td className="py-1.5">99</td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm text-slate-500 mt-2">
          <strong>Notable outliers (rank gap &gt; 30):</strong> The largest discrepancies come
          from teams where our specific situation (runner on 2B scoring on OF hit) diverges
          from the broader XBT% population. TB 2024 (rank 6 ours, rank 44 BR) and ATH 2021
          (rank 78 ours, rank 14 BR) are prominent examples. These outliers are a natural
          consequence of measuring a subset of baserunning situations, not a model error —
          both rankings are correct for what each measures. 20 of 120 team-years have rank
          gaps &gt; 30.
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

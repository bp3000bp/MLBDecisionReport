import type { DecisionModule } from "./types";

export const stealAttemptModule: DecisionModule = {
  id: "steal-attempt",
  slug: "steal-attempt",
  name: "Steal Attempt Grader",
  tagline: "Grading stolen-base attempts by expected value",
  description:
    "Every stolen base attempt carries a break-even probability: the success rate " +
    "at which the attempt is worth the risk. We grade each attempt against that " +
    "threshold using empirical success rates binned by runner sprint speed, " +
    "catcher pop time, and outs.",
  status: "live",
  primaryMetric: "run_value_per100",
  primaryMetricLabel: "Run Value / 100 Att",
  primaryMetricDescription:
    "Expected run value added per 100 steal attempts. Positive = attempts added value; " +
    "negative = attempts hurt the team on average.",
  headlineFinding:
    "Most steal attempts (2020–2025) were positive expected value decisions. " +
    "The steals that hurt teams most often came from slower runners facing elite catchers " +
    "— situations where the success rate fell below the RE24 break-even threshold.",
  dateRange: "2020–2026",
  secondaryLeaderboardLabel: "Runner",
  teamColumns: [
    { key: "batting_team",   label: "Team",        description: "Team abbreviation",                        format: "string",  sortable: true },
    { key: "game_year",      label: "Year",        description: "Season",                                   format: "year",    sortable: true },
    { key: "n_attempts",     label: "Att",         description: "Total steal attempts (2B + 3B)",           format: "integer", sortable: true },
    { key: "success_rate",   label: "SB%",         description: "Fraction of attempts that succeeded",      format: "percent", sortable: true },
    { key: "good_steal_rate",label: "Good%",       description: "Fraction of attempts with P(safe) > break-even", format: "percent", sortable: true, color: "gradient-send" },
    { key: "run_value_per100",label: "RV/100",     description: "Expected run value per 100 attempts",      format: "runs",    sortable: true, defaultSort: "desc" },
    { key: "bad_steal_runs_per100", label: "Bad Cost/100", description: "Run value lost on below-break-even attempts per 100 (negative = cost)", format: "runs", sortable: true },
    { key: "total_run_value",label: "Total RV",    description: "Total run value of all steal attempts",    format: "runs",    sortable: true },
  ],
  coachColumns: [
    { key: "runner_name",    label: "Runner",      description: "Player name",                              format: "string",  sortable: true },
    { key: "n_attempts",     label: "Att",         description: "Career steal attempts (2B + 3B, 2020–2026)", format: "integer", sortable: true },
    { key: "success_rate",   label: "SB%",         description: "Career success rate",                      format: "percent", sortable: true },
    { key: "good_steal_rate",label: "Good%",       description: "Fraction of attempts above break-even",   format: "percent", sortable: true, color: "gradient-send" },
    { key: "run_value_per100",label: "RV/100",     description: "Expected run value per 100 attempts",      format: "runs",    sortable: true, defaultSort: "desc" },
    { key: "bad_steal_runs_per100", label: "Bad Cost/100", description: "Run value lost on bad attempts per 100", format: "runs", sortable: true },
    { key: "total_run_value",label: "Career RV",   description: "Career total run value from steal attempts", format: "runs",  sortable: true },
  ],
};

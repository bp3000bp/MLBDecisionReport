import type { DecisionModule } from "./types";

export const ibbModule: DecisionModule = {
  id: "ibb",
  slug: "ibb",
  name: "IBB Decision Grader",
  tagline: "Was that intentional walk worth the run-expectancy cost?",
  description:
    "Every intentional walk raises the batting team's run expectancy. We ask whether " +
    "the matchup advantage gained — bypassing a dangerous batter to face a weaker one — " +
    "exceeded that cost. Graded against RE24 break-even using season wOBA for both " +
    "the walked batter and the on-deck hitter.",
  status: "live",
  primaryMetric: "run_value_per100",
  primaryMetricLabel: "Run Value / 100 IBBs",
  primaryMetricDescription:
    "Expected run value per 100 intentional walks issued. Positive = IBBs added value on net; " +
    "negative = IBBs cost the team runs on net.",
  headlineFinding:
    "97.5% of intentional walks (2020–2026) were value-negative: the run-expectancy cost " +
    "of adding a baserunner (avg +0.17 RE) almost always exceeded the matchup gain from " +
    "bypassing the walked batter. The average IBB costs the issuing team about 0.14 " +
    "expected runs. This is consistent with the sabermetric consensus — and explains " +
    "why IBB usage has fallen 45% since the 2017 automatic-walk rule.",
  dateRange: "2020–2026",
  secondaryLeaderboardLabel: undefined,
  teamColumns: [
    { key: "fielding_team",       label: "Team",        description: "Team that issued the intentional walks",        format: "string",  sortable: true },
    { key: "game_year",           label: "Year",        description: "Season",                                        format: "year",    sortable: true },
    { key: "n_ibb",               label: "IBBs",        description: "Total intentional walks issued",                format: "integer", sortable: true },
    { key: "good_ibb_rate",       label: "Good%",       description: "Fraction of IBBs that saved runs (positive expected value)", format: "percent", sortable: true, color: "gradient-send" },
    { key: "avg_re_cost",         label: "Avg RE Cost", description: "Average run-expectancy cost per IBB",           format: "runs",    sortable: true },
    { key: "run_value_per100",    label: "RV/100",      description: "Expected run value per 100 IBBs issued",        format: "runs",    sortable: true, defaultSort: "desc" },
    { key: "total_run_value",     label: "Total RV",    description: "Total run value from all IBB decisions",        format: "runs",    sortable: true },
  ],
  coachColumns: [],
};

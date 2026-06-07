import type { DecisionModule } from "./types";

export const sendHoldModule: DecisionModule = {
  id: "send-hold",
  slug: "send-hold",
  name: "Send/Hold Grader",
  tagline: "Grading third-base coach decisions on extra-base opportunities",
  description:
    "Every time a runner on second base can attempt to score on an outfield hit, " +
    "the third-base coach makes a decision. We grade each call against the break-even " +
    "probability from run expectancy — the point where sending becomes the correct choice.",
  status: "live",
  primaryMetric: "bad_hold_runs_per100",
  primaryMetricLabel: "Runs Left/100 Opp",
  primaryMetricDescription:
    "Expected run value left on the table by holding runners who should have been sent, " +
    "per 100 opportunities. Higher = more conservative (and more costly).",
  headlineFinding:
    "In every situation we analyzed, the empirical probability of scoring " +
    "exceeded the break-even threshold. Every run lost came from holding too often — " +
    "not from sending at the wrong time.",
  dateRange: "2020–2026",
  teamColumns: [
    { key: "batting_team", label: "Team", description: "Team abbreviation", format: "string", sortable: true },
    { key: "game_year", label: "Year", description: "Season", format: "year", sortable: true },
    { key: "coach_name", label: "3B Coach", description: "Third-base coach", format: "string", sortable: true },
    { key: "n_opportunities", label: "Opp", description: "Graded opportunities", format: "integer", sortable: true },
    { key: "send_rate", label: "Send%", description: "Fraction of opportunities where runner was sent", format: "percent", sortable: true, color: "gradient-send" },
    { key: "safe_rate", label: "Safe%", description: "Fraction of sent runners who scored", format: "percent", sortable: true },
    { key: "bad_hold_runs_per100", label: "Runs Left/100", description: "Run value left on table per 100 opportunities", format: "runs", sortable: true, color: "gradient-bad-hold", defaultSort: "desc" },
    { key: "bad_hold_runs", label: "Total Runs Left", description: "Total run value left on table by over-holding", format: "runs", sortable: true },
  ],
  coachColumns: [
    { key: "coach_name", label: "Coach", description: "Third-base coach", format: "string", sortable: true },
    { key: "seasons_coached", label: "Seasons", description: "Seasons in dataset", format: "integer", sortable: true },
    { key: "n_opportunities", label: "Opp", description: "Career graded opportunities", format: "integer", sortable: true },
    { key: "send_rate", label: "Send%", description: "Fraction of opportunities where runner was sent", format: "percent", sortable: true, color: "gradient-send" },
    { key: "safe_rate", label: "Safe%", description: "Fraction of sent runners who scored", format: "percent", sortable: true },
    { key: "bad_hold_runs_per100", label: "Runs Left/100", description: "Run value left on table per 100 opportunities", format: "runs", sortable: true, color: "gradient-bad-hold", defaultSort: "desc" },
    { key: "bad_hold_runs", label: "Total Runs Left", description: "Total run value left on table by over-holding", format: "runs", sortable: true },
  ],
};

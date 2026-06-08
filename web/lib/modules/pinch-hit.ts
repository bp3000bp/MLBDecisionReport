import type { DecisionModule } from "./types";

export const pinchHitModule: DecisionModule = {
  id: "pinch-hit",
  slug: "pinch-hit",
  name: "Pinch Hit Grader",
  tagline: "Did the pinch hit substitution improve expected offense given the pitcher matchup?",
  description:
    "Every pinch hit appearance is a decision. The manager pulls a hitter and sends up " +
    "a substitute — but does the pinch hitter represent a genuine offensive upgrade " +
    "against this specific pitcher (accounting for handedness) given the base-out state? " +
    "We grade each substitution against the wOBA-against matchup and the RE24 run value " +
    "of the situation.",
  status: "coming-soon",
  primaryMetric: "run_value_per100",
  primaryMetricLabel: "Run Value / 100 PH",
  primaryMetricDescription:
    "Expected run value gained (or lost) per 100 pinch hit substitutions. Positive = " +
    "the pinch hit call improved expected offense; negative = the replaced batter would " +
    "have been a better matchup.",
  headlineFinding:
    "Pipeline in development. Grading every pinch hit appearance against the platoon-adjusted " +
    "wOBA matchup and the RE24 run value of the base-out state.",
  dateRange: "2020–2026",
  teamColumns: [
    { key: "batting_team",     label: "Team",       description: "Team making the pinch hit substitution",                  format: "string",  sortable: true },
    { key: "game_year",        label: "Year",       description: "Season",                                                   format: "year",    sortable: true },
    { key: "n_ph",             label: "PH",         description: "Total pinch hit appearances",                              format: "integer", sortable: true },
    { key: "good_ph_rate",     label: "Good%",      description: "Fraction of pinch hit calls that improved expected offense", format: "percent", sortable: true },
    { key: "avg_woba_gain",    label: "Avg wOBA+",  description: "Average wOBA improvement from the substitution",           format: "number",  sortable: true },
    { key: "run_value_per100", label: "RV/100",     description: "Expected run value per 100 pinch hit substitutions",       format: "runs",    sortable: true, defaultSort: "desc" },
  ],
  coachColumns: [],
};

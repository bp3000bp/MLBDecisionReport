export interface DecisionModule {
  id: string;
  slug: string;
  name: string;
  tagline: string;
  description: string;
  status: "live" | "coming-soon";
  primaryMetric: string;
  primaryMetricLabel: string;
  primaryMetricDescription: string;
  headlineFinding: string;
  dateRange: string;
  teamColumns: ColumnDef[];
  /** Second leaderboard tab label (defaults to "Coach") */
  secondaryLeaderboardLabel?: string;
  coachColumns: ColumnDef[];
}

export interface ColumnDef {
  key: string;
  label: string;
  description: string;
  format: "number" | "percent" | "runs" | "string" | "integer" | "year";
  sortable: boolean;
  color?: "gradient-bad-hold" | "gradient-send" | "neutral";
  defaultSort?: "asc" | "desc";
}

export interface TeamRow {
  batting_team: string;
  game_year: number;
  coach_name?: string;
  n_opportunities: number;
  n_sent: number;
  n_held: number;
  n_bad_send: number;
  n_bad_hold: number;
  bad_send_runs: number;
  bad_hold_runs: number;
  net_run_value: number;
  bad_hold_runs_per100: number;
  bad_send_runs_per100: number;
  net_run_value_per100: number;
  safe_rate: number;
  send_rate: number;
  low_sample: boolean;
  short_season: boolean;
}

export interface CoachRow {
  coach_name: string;
  seasons_coached: number;
  n_opportunities: number;
  n_sent: number;
  n_held: number;
  n_bad_send: number;
  n_bad_hold: number;
  bad_send_runs: number;
  bad_hold_runs: number;
  net_run_value: number;
  bad_hold_runs_per100: number;
  bad_send_runs_per100: number;
  net_run_value_per100: number;
  safe_rate: number;
  send_rate: number;
  low_sample: boolean;
}

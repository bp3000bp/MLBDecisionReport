import fs from "fs";
import path from "path";
import type { TeamRow, CoachRow } from "./modules/types";

const DATA_DIR = path.join(process.cwd(), "data");

function readJson<T>(filename: string): T[] {
  const filepath = path.join(DATA_DIR, filename);
  if (!fs.existsSync(filepath)) return [];
  return JSON.parse(fs.readFileSync(filepath, "utf-8")) as T[];
}

function readJsonObject<T>(filename: string): T | null {
  const filepath = path.join(DATA_DIR, filename);
  if (!fs.existsSync(filepath)) return null;
  return JSON.parse(fs.readFileSync(filepath, "utf-8")) as T;
}

export interface PipelineMeta {
  last_updated: string;   // ISO date "YYYY-MM-DD"
  current_year: number;
  send_hold_years: number[];
  steal_years: number[];
}

export function getMeta(): PipelineMeta | null {
  return readJsonObject<PipelineMeta>("meta.json");
}

// Send/Hold module
export function getTeamLeaderboard(): TeamRow[] {
  return readJson<TeamRow>("leaderboard_team.json");
}

export function getCoachLeaderboard(): CoachRow[] {
  return readJson<CoachRow>("leaderboard_coach.json");
}

// Steal Attempt module
export function getStealTeamLeaderboard(): Record<string, unknown>[] {
  return readJson<Record<string, unknown>>("leaderboard_steal_team.json");
}

export function getStealRunnerLeaderboard(): Record<string, unknown>[] {
  return readJson<Record<string, unknown>>("leaderboard_steal_runner.json");
}

// IBB Decision module
export function getIbbTeamLeaderboard(): Record<string, unknown>[] {
  return readJson<Record<string, unknown>>("leaderboard_ibb_team.json");
}

// Pinch Hit module
export function getPinchHitTeamLeaderboard(): Record<string, unknown>[] {
  return readJson<Record<string, unknown>>("leaderboard_pinch_hit_team.json");
}

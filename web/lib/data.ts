import fs from "fs";
import path from "path";
import type { TeamRow, CoachRow } from "./modules/types";

const DATA_DIR = path.join(process.cwd(), "data");

function readJson<T>(filename: string): T[] {
  const filepath = path.join(DATA_DIR, filename);
  if (!fs.existsSync(filepath)) return [];
  return JSON.parse(fs.readFileSync(filepath, "utf-8")) as T[];
}

export function getTeamLeaderboard(): TeamRow[] {
  return readJson<TeamRow>("leaderboard_team.json");
}

export function getCoachLeaderboard(): CoachRow[] {
  return readJson<CoachRow>("leaderboard_coach.json");
}

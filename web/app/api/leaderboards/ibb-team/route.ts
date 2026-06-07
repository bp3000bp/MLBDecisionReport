import { NextResponse } from "next/server";
import { getIbbTeamLeaderboard } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const year = searchParams.get("year");
  const team = searchParams.get("team");

  let rows = getIbbTeamLeaderboard();

  if (year && year !== "all") {
    rows = rows.filter((r) => String(r.game_year) === year);
  }
  if (team) {
    rows = rows.filter((r) => r.fielding_team === team);
  }

  return NextResponse.json(rows);
}

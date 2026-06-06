import { NextResponse } from "next/server";
import { getTeamLeaderboard } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const year = searchParams.get("year");
  const team = searchParams.get("team");

  let rows = getTeamLeaderboard();

  if (year && year !== "all") {
    rows = rows.filter((r) => String(r.game_year) === year);
  }
  if (team) {
    rows = rows.filter((r) => r.batting_team === team);
  }

  return NextResponse.json(rows);
}

import { NextResponse } from "next/server";
import { getCoachLeaderboard } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const coach = searchParams.get("coach");

  let rows = getCoachLeaderboard();

  if (coach) {
    rows = rows.filter((r) =>
      r.coach_name.toLowerCase().includes(coach.toLowerCase())
    );
  }

  return NextResponse.json(rows);
}

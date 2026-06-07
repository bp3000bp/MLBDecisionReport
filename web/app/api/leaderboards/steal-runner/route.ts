import { NextResponse } from "next/server";
import { getStealRunnerLeaderboard } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const search = searchParams.get("search");
  const minAtt = Number(searchParams.get("min_att") ?? "0");

  let rows = getStealRunnerLeaderboard();

  if (search) {
    const q = search.toLowerCase();
    rows = rows.filter((r) => String(r.runner_name ?? "").toLowerCase().includes(q));
  }
  if (minAtt > 0) {
    rows = rows.filter((r) => Number(r.n_attempts) >= minAtt);
  }

  return NextResponse.json(rows);
}

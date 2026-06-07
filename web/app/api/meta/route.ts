import { NextResponse } from "next/server";
import { getMeta } from "@/lib/data";

export async function GET() {
  const meta = getMeta();
  if (!meta) {
    return NextResponse.json({ last_updated: null, current_year: new Date().getFullYear(), send_hold_years: [], steal_years: [] });
  }
  return NextResponse.json(meta);
}

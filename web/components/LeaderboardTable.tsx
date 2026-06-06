"use client";

import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown, AlertTriangle, Info } from "lucide-react";
import type { ColumnDef } from "@/lib/modules/types";

type SortDir = "asc" | "desc";

interface Props {
  rows: Record<string, unknown>[];
  columns: ColumnDef[];
  defaultSortKey?: string;
  defaultSortDir?: SortDir;
}

function formatValue(value: unknown, format: ColumnDef["format"]): string {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  switch (format) {
    case "percent":  return isNaN(n) ? String(value) : `${(n * 100).toFixed(1)}%`;
    case "runs":     return isNaN(n) ? String(value) : n.toFixed(2);
    case "integer":  return isNaN(n) ? String(value) : Math.round(n).toLocaleString();
    case "number":   return isNaN(n) ? String(value) : n.toFixed(3);
    default:         return String(value);
  }
}

function metricColor(key: string, color: ColumnDef["color"], value: unknown): string {
  if (!color) return "";
  const n = Number(value);
  if (isNaN(n)) return "";

  if (color === "gradient-bad-hold") {
    if (n < 4.5)  return "text-emerald-700 font-semibold";
    if (n < 7.0)  return "text-amber-700 font-semibold";
    return "text-red-700 font-semibold";
  }
  if (color === "gradient-send") {
    if (n > 0.85) return "text-emerald-700";
    if (n < 0.70) return "text-red-700";
    return "text-amber-700";
  }
  return "";
}

export default function LeaderboardTable({ rows, columns, defaultSortKey, defaultSortDir = "desc" }: Props) {
  const initKey = defaultSortKey ?? columns.find((c) => c.defaultSort)?.key ?? columns[0].key;
  const [sortKey, setSortKey] = useState<string>(initKey);
  const [sortDir, setSortDir] = useState<SortDir>(defaultSortDir);
  const [search, setSearch] = useState("");
  const [yearFilter, setYearFilter] = useState("all");
  const [tooltip, setTooltip] = useState<string | null>(null);

  const years = useMemo(() => {
    const ys = Array.from(new Set(rows.map((r) => r.game_year as number))).filter(Boolean).sort();
    return ys;
  }, [rows]);

  const filtered = useMemo(() => {
    let data = rows;
    if (search) {
      const q = search.toLowerCase();
      data = data.filter((r) =>
        Object.values(r).some((v) => String(v).toLowerCase().includes(q))
      );
    }
    if (yearFilter !== "all") {
      data = data.filter((r) => String(r.game_year) === yearFilter);
    }
    return [...data].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const an = Number(av);
      const bn = Number(bv);
      const numeric = !isNaN(an) && !isNaN(bn);
      const cmp = numeric ? an - bn : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [rows, search, yearFilter, sortKey, sortDir]);

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      const col = columns.find((c) => c.key === key);
      setSortDir(col?.defaultSort ?? "desc");
    }
  }

  function SortIcon({ col }: { col: ColumnDef }) {
    if (!col.sortable) return null;
    if (sortKey !== col.key) return <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 ml-1 inline" />;
    return sortDir === "asc"
      ? <ChevronUp className="h-3.5 w-3.5 text-blue-600 ml-1 inline" />
      : <ChevronDown className="h-3.5 w-3.5 text-blue-600 ml-1 inline" />;
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {years.length > 1 && (
          <select
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All years</option>
            {years.map((y) => (
              <option key={y} value={String(y)}>{y}</option>
            ))}
          </select>
        )}
        <span className="text-sm text-slate-500 ml-auto">{filtered.length} rows</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="w-8 pl-3 py-3 text-slate-400 font-normal text-left">#</th>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && toggleSort(col.key)}
                  className={`px-3 py-3 text-left font-medium text-slate-700 whitespace-nowrap ${col.sortable ? "cursor-pointer select-none hover:text-slate-900" : ""}`}
                >
                  <span className="inline-flex items-center gap-0.5">
                    {col.label}
                    <SortIcon col={col} />
                    <button
                      onClick={(e) => { e.stopPropagation(); setTooltip(tooltip === col.key ? null : col.key); }}
                      className="ml-1 text-slate-400 hover:text-slate-600"
                    >
                      <Info className="h-3 w-3 inline" />
                    </button>
                  </span>
                  {tooltip === col.key && (
                    <div className="absolute z-10 mt-1 max-w-xs bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg">
                      {col.description}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((row, i) => (
              <tr key={i} className="hover:bg-slate-50 transition-colors">
                <td className="pl-3 py-2.5 text-slate-400 text-xs">{i + 1}</td>
                {columns.map((col) => {
                  const val = row[col.key];
                  const isLow = row.low_sample as boolean;
                  const isShort = row.short_season as boolean;
                  return (
                    <td key={col.key} className={`px-3 py-2.5 ${metricColor(col.key, col.color, val)}`}>
                      {col.key === "batting_team" || col.key === "coach_name" ? (
                        <div className="flex items-center gap-1.5">
                          <span>{String(val ?? "—")}</span>
                          {isLow && col.key === "batting_team" && (
                            <span title="Small sample (<150 opportunities)" className="inline-flex items-center gap-0.5 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
                              <AlertTriangle className="h-3 w-3" />
                              <span>Low</span>
                            </span>
                          )}
                          {isShort && col.key === "batting_team" && (
                            <span title="2020 — 60-game season" className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full">60g</span>
                          )}
                          {isLow && col.key === "coach_name" && (
                            <span title="Small sample (<150 opportunities)" className="inline-flex items-center gap-0.5 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
                              <AlertTriangle className="h-3 w-3" />
                              <span>Low</span>
                            </span>
                          )}
                        </div>
                      ) : (
                        formatValue(val, col.format)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="text-center py-8 text-slate-400">No results</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

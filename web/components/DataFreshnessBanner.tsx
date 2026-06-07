"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

interface Meta {
  last_updated: string | null;
  current_year: number;
}

export default function DataFreshnessBanner() {
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    fetch("/api/meta")
      .then((r) => r.json())
      .then(setMeta)
      .catch(() => null);
  }, []);

  if (!meta?.last_updated) return null;

  const updated = new Date(meta.last_updated + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round((today.getTime() - updated.getTime()) / 86400000);

  const label = diffDays === 0
    ? "Updated today"
    : diffDays === 1
    ? "Updated yesterday"
    : `Updated ${meta.last_updated}`;

  const isStale = diffDays > 2;

  return (
    <div className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${
      isStale
        ? "bg-amber-50 border-amber-200 text-amber-700"
        : "bg-blue-50 border-blue-200 text-blue-700"
    }`}>
      <RefreshCw className="h-3 w-3" />
      <span>{label} · {meta.current_year} data refreshes daily</span>
    </div>
  );
}

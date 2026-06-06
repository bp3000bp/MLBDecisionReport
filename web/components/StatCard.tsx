interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: "blue" | "green" | "amber" | "red";
}

const accentMap = {
  blue:  "text-blue-700 bg-blue-50 border-blue-100",
  green: "text-emerald-700 bg-emerald-50 border-emerald-100",
  amber: "text-amber-700 bg-amber-50 border-amber-100",
  red:   "text-red-700 bg-red-50 border-red-100",
};

export default function StatCard({ label, value, sub, accent = "blue" }: Props) {
  return (
    <div className={`rounded-xl border p-4 ${accentMap[accent]}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-70">{sub}</p>}
    </div>
  );
}

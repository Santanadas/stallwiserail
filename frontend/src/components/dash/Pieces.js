/** Shared presentation pieces for the console. Every number handed to these
 *  comes from /api/dashboard/summary — nothing here invents a value. */

export const inr = (n) => `₹${Math.round(Number(n) || 0).toLocaleString("en-IN")}`;

export function Card({ title, hint, right, children, className = "", testId }) {
  return (
    <section
      data-testid={testId}
      className={`overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm ${className}`}
    >
      {(title || right) && (
        <div className="flex items-center justify-between gap-3 border-b border-neutral-100 px-5 py-3.5">
          <div className="min-w-0">
            {title && <h2 className="mk-head text-sm font-black tracking-tight text-[#0A0A0A]">{title}</h2>}
            {hint && <p className="mt-0.5 text-[11px] font-medium text-neutral-400">{hint}</p>}
          </div>
          {right}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Stat({ label, value, delta, foot }) {
  return (
    <div className="flex flex-col gap-1.5 px-5 py-4">
      <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-neutral-400">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="mk-head text-2xl font-black tracking-tight text-[#0A0A0A] sm:text-[28px]">{value}</span>
        {delta != null && (
          <span className={`text-xs font-bold ${delta >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
            {delta >= 0 ? "+" : "−"}{Math.abs(delta)}%
          </span>
        )}
      </div>
      {foot && <span className="text-[11px] font-medium text-neutral-400">{foot}</span>}
    </div>
  );
}

/** Single-series area chart. One hue, recessive grid, only the last point
 *  labelled — a number on every point is noise at this size. */
export function Sparkline({ points, height = 190 }) {
  const data = points || [];
  const max = Math.max(1, ...data.map((d) => d.amount));
  const W = 700;
  const top = 12;
  const bottom = height - 26;
  const left = 42;
  const step = data.length > 1 ? (W - left - 16) / (data.length - 1) : 0;
  const xy = data.map((d, i) => [
    left + i * step,
    bottom - (d.amount / max) * (bottom - top),
  ]);
  const line = xy.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L ");
  const last = data[data.length - 1];
  const gridY = [top, top + (bottom - top) / 2, bottom];

  return (
    <div>
      <svg width="100%" height={height} viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" className="block overflow-visible">
        {gridY.map((y, i) => (
          <line key={y} x1={left} y1={y} x2={W} y2={y} stroke={i === 2 ? "#E5E5E5" : "#F5F5F5"} strokeWidth="1" />
        ))}
        <text x={left - 6} y={top + 4} textAnchor="end" fontSize="10" fontWeight="600" fill="#A3A3A3">{inr(max)}</text>
        <text x={left - 6} y={bottom + 4} textAnchor="end" fontSize="10" fontWeight="600" fill="#A3A3A3">0</text>
        {data.length > 1 && (
          <>
            <path d={`M ${line} L ${xy[xy.length - 1][0].toFixed(1)} ${bottom} L ${left} ${bottom} Z`} fill="#FF4F00" fillOpacity="0.07" />
            <path d={`M ${line}`} fill="none" stroke="#FF4F00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx={xy[xy.length - 1][0]} cy={xy[xy.length - 1][1]} r="4" fill="#FF4F00" stroke="#fff" strokeWidth="2" />
          </>
        )}
      </svg>
      <div className="flex justify-between pl-[42px] pt-2">
        <span className="text-[10px] font-semibold text-neutral-400">
          {data[0] ? new Date(data[0].date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : ""}
        </span>
        <span className="text-[10px] font-bold text-neutral-600">
          {last ? `${new Date(last.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} · ${inr(last.amount)}` : ""}
        </span>
      </div>
    </div>
  );
}

/** Horizontal magnitude bars: one hue, shaded by rank, always directly labelled. */
export function BarList({ rows, empty = "Nothing yet." }) {
  const shades = ["#FF4F00", "#FF7A3D", "#FFA478", "#FFC9AC", "#FFE0CF"];
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length) return <p className="text-xs font-medium text-neutral-400">{empty}</p>;
  return (
    <div className="flex flex-col gap-3.5">
      {rows.map((r, i) => (
        <div key={r.label} className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="truncate text-xs font-bold text-[#0A0A0A]">{r.label}</span>
            <span className="shrink-0 text-xs font-bold text-neutral-600">{r.display}</span>
          </div>
          <div className="h-[9px] overflow-hidden rounded-[5px] bg-neutral-100">
            <div
              className="h-[9px] rounded-[5px]"
              style={{ width: `${Math.max(4, (r.value / max) * 100)}%`, background: shades[i] || shades[4] }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-xl bg-neutral-100 ${className}`} />;
}

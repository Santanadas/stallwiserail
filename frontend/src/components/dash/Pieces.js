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

/** Single-series area chart.
 *
 * The plot stretches to the container with preserveAspectRatio="none", which
 * would distort any text inside the SVG — squashing the axis labels on a phone
 * and stretching them on a wide screen. So the graphics live in the SVG and
 * every label is HTML positioned over it.
 */
export function Sparkline({ points, height = 190 }) {
  const data = points || [];
  const max = Math.max(1, ...data.map((d) => d.amount));
  const W = 700;
  const top = 8;
  const bottom = height - 8;
  const step = data.length > 1 ? W / (data.length - 1) : 0;
  const xy = data.map((d, i) => [i * step, bottom - (d.amount / max) * (bottom - top)]);
  const line = xy.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L ");
  const last = data[data.length - 1];
  const fmtDay = (iso) =>
    iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "";

  return (
    <div>
      <div className="flex gap-2">
        {/* Y axis — HTML, so it never distorts with the plot */}
        <div
          className="flex shrink-0 flex-col justify-between py-px text-right text-[10px] font-semibold text-neutral-400"
          style={{ height }}
        >
          <span>{inr(max)}</span>
          <span>{inr(max / 2)}</span>
          <span>0</span>
        </div>
        <div className="relative min-w-0 flex-1">
          {/* Grid — also HTML, so the hairlines stay 1px at every width */}
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-between">
            <div className="h-px bg-neutral-100" />
            <div className="h-px bg-neutral-100" />
            <div className="h-px bg-neutral-200" />
          </div>
          <svg
            width="100%"
            height={height}
            viewBox={`0 0 ${W} ${height}`}
            preserveAspectRatio="none"
            className="relative block"
            role="img"
            aria-label={`Sales per day. Latest ${fmtDay(last?.date)}: ${inr(last?.amount || 0)}`}
          >
            {data.length > 1 && (
              <>
                <path d={`M ${line} L ${W} ${bottom} L 0 ${bottom} Z`} fill="#FF4F00" fillOpacity="0.07" />
                {/* vectorEffect keeps the stroke 2px however far the plot is stretched */}
                <path
                  d={`M ${line}`}
                  fill="none"
                  stroke="#FF4F00"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              </>
            )}
          </svg>
          {data.length > 1 && (
            <span
              className="pointer-events-none absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[#FF4F00]"
              style={{ left: "100%", top: `${((xy[xy.length - 1][1] - 0) / height) * 100}%` }}
            />
          )}
        </div>
      </div>
      <div className="flex justify-between pl-[46px] pt-2">
        <span className="text-[10px] font-semibold text-neutral-400">{fmtDay(data[0]?.date)}</span>
        <span className="text-[10px] font-bold text-neutral-600">
          {last ? `${fmtDay(last.date)} · ${inr(last.amount)}` : ""}
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

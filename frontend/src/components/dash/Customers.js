import { Card, Skeleton, inr } from "./Pieces";

/** Buyers, aggregated from real orders — who came back, and what they spent. */
export default function CustomersSection({ summary, loading }) {
  if (!loading && !summary) {
    return (
      <div className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 p-10 text-center text-sm font-medium text-neutral-600">
        Couldn&apos;t load this right now. Reload the page to try again.
      </div>
    );
  }
  if (loading || !summary) return <Skeleton className="h-[320px]" />;

  const rows = summary.customers || [];
  const { metrics } = summary;

  if (!rows.length) {
    return (
      <Card title="Customers">
        <p className="py-6 text-center text-sm font-medium text-neutral-500">
          Nobody has bought yet. Once an order is paid, the buyer appears here.
        </p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="grid divide-y divide-neutral-100 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm sm:grid-cols-3 sm:divide-y-0 sm:divide-x">
        <div className="flex flex-col gap-1.5 px-5 py-4">
          <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-neutral-400">Buyers</span>
          <span className="mk-head text-[28px] font-black tracking-tight text-[#0A0A0A]">{metrics.uniqueBuyers}</span>
        </div>
        <div className="flex flex-col gap-1.5 px-5 py-4">
          <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-neutral-400">Came back</span>
          <span className="mk-head text-[28px] font-black tracking-tight text-[#0A0A0A]">{metrics.repeatBuyers}</span>
          <span className="text-[11px] font-medium text-neutral-400">
            {metrics.uniqueBuyers ? Math.round((metrics.repeatBuyers / metrics.uniqueBuyers) * 100) : 0}% of buyers
          </span>
        </div>
        <div className="flex flex-col gap-1.5 px-5 py-4">
          <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-neutral-400">Average spend</span>
          <span className="mk-head text-[28px] font-black tracking-tight text-[#0A0A0A]">
            {inr(rows.reduce((s, c) => s + c.spend, 0) / rows.length)}
          </span>
        </div>
      </section>

      <Card title="Everyone who has bought" hint="Most valuable first">
        <div className="-mx-5 -mb-5 overflow-x-auto">
          <table className="w-full min-w-[560px]">
            <thead>
              <tr className="border-y border-neutral-100 bg-neutral-50/60">
                {["Buyer", "City", "Orders", "Spent", "Last order"].map((h, i) => (
                  <th key={h} className={`px-5 py-2.5 text-[10px] font-bold uppercase tracking-[0.06em] text-neutral-400 ${i > 1 ? "text-right" : "text-left"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {rows.map((c) => (
                <tr key={c.email}>
                  <td className="px-5 py-3">
                    <div className="text-[13px] font-bold text-[#0A0A0A]">{c.name || "Buyer"}</div>
                    <div className="text-[11px] font-medium text-neutral-400">{c.email}</div>
                  </td>
                  <td className="px-5 py-3 text-xs font-medium text-neutral-600">{c.city || "—"}</td>
                  <td className="px-5 py-3 text-right text-xs font-bold text-neutral-700">
                    {c.orders}
                    {c.orders > 1 && (
                      <span className="ml-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700">
                        repeat
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-right text-[13px] font-extrabold text-[#0A0A0A]">{inr(c.spend)}</td>
                  <td className="px-5 py-3 text-right text-xs font-medium text-neutral-500">
                    {c.lastAt ? new Date(c.lastAt).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

import { Card, Stat, Sparkline, BarList, Skeleton, inr } from "./Pieces";

const METHOD_LABELS = { online: "Paid online (UPI, card, netbanking)", cod: "Cash on delivery" };

export default function InsightsSection({ summary, loading }) {
  if (!loading && !summary) {
    return (
      <div className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 p-10 text-center text-sm font-medium text-neutral-600">
        Couldn&apos;t load this right now. Reload the page to try again.
      </div>
    );
  }
  if (loading || !summary) {
    return <div className="flex flex-col gap-5"><Skeleton className="h-[120px]" /><Skeleton className="h-[340px]" /></div>;
  }
  const { metrics, daily, topProducts, paymentMix, topCities, counts } = summary;
  const totalMix = paymentMix.reduce((s, m) => s + m.orders, 0);

  const growth = metrics.grossLastMonth > 0
    ? Math.round(((metrics.grossThisMonth - metrics.grossLastMonth) / metrics.grossLastMonth) * 100) : null;
  const repeatPct = metrics.uniqueBuyers
    ? Math.round((metrics.repeatBuyers / metrics.uniqueBuyers) * 100) : 0;

  return (
    <div className="flex flex-col gap-5">
      <section className="grid divide-y divide-neutral-100 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4 xl:divide-x">
        <Stat label="Revenue this month" value={inr(metrics.grossThisMonth)} delta={growth} />
        <Stat label="Orders" value={metrics.ordersThisMonth}
          foot={`${counts.byStatus.completed} completed all time`} />
        <Stat label="Repeat buyers" value={`${repeatPct}%`}
          foot={`${metrics.repeatBuyers} of ${metrics.uniqueBuyers} came back`} />
        <Stat label="Dispute rate" value={`${metrics.disputeRate}%`}
          foot={`${counts.byStatus.disputed} of ${metrics.totalOrders} orders`} />
      </section>

      <Card title="Revenue per day" hint="Last 30 days · paid and completed orders">
        <Sparkline points={daily} height={250} />
      </Card>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card title="Best sellers" hint="By revenue">
          <BarList
            rows={topProducts.map((p) => ({
              label: p.title, value: p.revenue,
              display: `${inr(p.revenue)} · ${p.units}`,
            }))}
            empty="No sales recorded yet."
          />
        </Card>

        <Card title="How buyers pay" hint={`${totalMix} order${totalMix === 1 ? "" : "s"}`}>
          <BarList
            rows={paymentMix.map((m) => ({
              label: METHOD_LABELS[m.method] || m.method,
              value: m.orders,
              display: `${m.orders}`,
            }))}
            empty="No paid orders yet."
          />
          {paymentMix.some((m) => m.method === "cod") && (
            <p className="mt-4 border-t border-neutral-100 pt-3.5 text-xs font-medium leading-relaxed text-neutral-500">
              Cash orders never pass through Razorpay, so you keep that money directly —
              commission on them is billed separately.
            </p>
          )}
        </Card>

        <Card title="Where your buyers are" hint="By city on the delivery address">
          <BarList
            rows={topCities.map((c) => ({ label: c.city, value: c.orders, display: `${c.orders}` }))}
            empty="No delivery addresses recorded yet."
          />
        </Card>
      </div>
    </div>
  );
}

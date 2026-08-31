import { Link } from "react-router-dom";
import { Truck, KeyRound, AlertTriangle, Check, Landmark, ArrowRight } from "lucide-react";
import { StatusPill } from "@/components/Kit";
import { Card, Stat, Sparkline, BarList, Skeleton, inr } from "./Pieces";

/**
 * Home answers "what do I have to do?" before "how am I doing?".
 *
 * The old overview opened with lifetime totals, which never tell a seller
 * whether they can close the laptop. The queue at the top does: when it is
 * empty, the day is done.
 */

function Task({ tone, icon: Icon, tag, headline, note, cta, onClick }) {
  const tones = {
    orange: ["border-[#FFD9C2]", "bg-[#FFF7ED]", "text-[#FF4F00]", "text-[#8A2200]"],
    purple: ["border-neutral-200", "bg-purple-50", "text-purple-700", "text-purple-700"],
    amber: ["border-neutral-200", "bg-amber-50", "text-amber-700", "text-amber-700"],
    emerald: ["border-neutral-200", "bg-emerald-50", "text-emerald-700", "text-emerald-700"],
    rose: ["border-rose-200", "bg-rose-50", "text-rose-700", "text-rose-700"],
  }[tone];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col gap-2.5 rounded-2xl border ${tones[0]} bg-white p-3.5 text-left transition-shadow hover:shadow-md`}
    >
      <div className="flex items-center gap-2">
        <span className={`flex h-6 w-6 items-center justify-center rounded-lg ${tones[1]}`}>
          <Icon className={`h-3.5 w-3.5 ${tones[2]}`} />
        </span>
        <span className={`text-xs font-bold ${tones[3]}`}>{tag}</span>
      </div>
      <div className="mk-head text-2xl font-black leading-none tracking-tight text-[#0A0A0A]">{headline}</div>
      <p className="text-[11px] font-medium leading-snug text-neutral-500">{note}</p>
      <span className="mt-auto inline-flex items-center gap-1 pt-1 text-xs font-extrabold text-[#C43D00]">
        {cta} <ArrowRight className="h-3 w-3" />
      </span>
    </button>
  );
}

function daysAgo(iso) {
  if (!iso) return null;
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  return d <= 0 ? "today" : d === 1 ? "1 day" : `${d} days`;
}

export default function HomeSection({ summary, loading, error, onRetry, orders, onNav, store }) {
  if (!loading && !summary) {
    // A failed request must not masquerade as a shop with nothing in it.
    return (
      <div className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 p-12 text-center">
        <AlertTriangle className="mx-auto h-9 w-9 text-rose-300" />
        <h3 className="mk-head mt-3 text-sm font-black text-[#0A0A0A]">Couldn&apos;t load your dashboard</h3>
        <p className="mt-1 text-xs font-medium text-neutral-600">
          {error || "Your shop and orders are safe — this is a connection problem."}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-xs font-bold text-neutral-800 hover:bg-neutral-50"
        >
          Try again
        </button>
      </div>
    );
  }
  if (loading || !summary) {
    return (
      <div className="flex flex-col gap-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[132px]" />)}
        </div>
        <Skeleton className="h-[110px]" />
        <div className="grid gap-5 xl:grid-cols-[1.62fr_1fr]"><Skeleton className="h-[300px]" /><Skeleton className="h-[300px]" /></div>
      </div>
    );
  }

  const { queue, metrics, money, daily, topProducts, health } = summary;
  const tasks = [];

  if (queue.toShip > 0) {
    tasks.push(
      <Task key="ship" tone="orange" icon={Truck} tag="Ship now"
        headline={`${queue.toShip} order${queue.toShip > 1 ? "s" : ""}`}
        note={queue.oldestToShipAt
          ? `Paid and waiting. Oldest is ${daysAgo(queue.oldestToShipAt)} old.`
          : "Paid and waiting to be packed."}
        cta="Open orders" onClick={() => onNav("orders")} />
    );
  }
  if (queue.awaitingOtp > 0) {
    tasks.push(
      <Task key="otp" tone="purple" icon={KeyRound} tag="Awaiting code"
        headline={`${queue.awaitingOtp} deliver${queue.awaitingOtp > 1 ? "ies" : "y"}`}
        note="Out for delivery. Enter the buyer's code to close it and release your money."
        cta="Enter code" onClick={() => onNav("orders")} />
    );
  }
  if (queue.lowStock + queue.outOfStock > 0) {
    tasks.push(
      <Task key="stock" tone="amber" icon={AlertTriangle} tag="Running out"
        headline={`${queue.lowStock + queue.outOfStock} product${queue.lowStock + queue.outOfStock > 1 ? "s" : ""}`}
        note={queue.lowStockTitles.length ? queue.lowStockTitles.join(", ") : "Low or out of stock."}
        cta="Restock" onClick={() => onNav("products")} />
    );
  }
  if (queue.disputed > 0) {
    tasks.push(
      <Task key="disp" tone="rose" icon={AlertTriangle} tag="Disputed"
        headline={`${queue.disputed} order${queue.disputed > 1 ? "s" : ""}`}
        note={`${inr(money.disputedValue)} is on hold until this is settled.`}
        cta="Review" onClick={() => onNav("orders")} />
    );
  }
  if (!queue.bankReady) {
    tasks.push(
      <Task key="bank" tone="amber" icon={Landmark} tag="Action needed"
        headline="Add your bank"
        note="Until this is done, money from online orders cannot reach you."
        cta="Add bank details" onClick={() => onNav("payouts")} />
    );
  }

  const growth = metrics.grossLastMonth > 0
    ? Math.round(((metrics.grossThisMonth - metrics.grossLastMonth) / metrics.grossLastMonth) * 100)
    : null;
  const orderGrowth = metrics.ordersLastMonth > 0
    ? Math.round(((metrics.ordersThisMonth - metrics.ordersLastMonth) / metrics.ordersLastMonth) * 100)
    : null;

  const healthItems = [
    ["Bank account verified", health.bankVerified],
    ["Shop description written", health.hasBio],
    ["At least one product listed", health.hasProducts],
    ["Products have photos", health.hasProductImages],
    ["Cash on delivery offered", health.codEnabled],
    ["GSTIN added", health.hasGstin],
  ];
  const healthDone = healthItems.filter(([, v]) => v).length;

  return (
    <div className="flex flex-col gap-5">
      {/* ---- Needs you today ---- */}
      <section>
        <div className="mb-2.5 flex items-baseline justify-between gap-3">
          <h2 className="text-[13px] font-extrabold uppercase tracking-[0.06em] text-neutral-600">Needs you today</h2>
          <span className="text-xs font-semibold text-neutral-400">
            {tasks.length ? "Clear these and you are done" : "All clear"}
          </span>
        </div>
        {tasks.length ? (
          <div className="grid gap-3 min-[440px]:grid-cols-2 xl:grid-cols-4">{tasks}</div>
        ) : (
          <div className="flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4">
            <Check className="h-5 w-5 shrink-0 text-emerald-600" />
            <div>
              <p className="text-sm font-bold text-emerald-900">Nothing needs you right now.</p>
              <p className="text-xs font-medium text-emerald-700">
                Every order is handled and nothing is running low.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* ---- KPI strip ---- */}
      <section className="grid divide-y divide-neutral-100 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4 xl:divide-x">
        <Stat label="Sales this month" value={inr(metrics.grossThisMonth)} delta={growth}
          foot={metrics.grossLastMonth ? `vs ${inr(metrics.grossLastMonth)} last month` : "First month of trading"} />
        <Stat label="Orders" value={metrics.ordersThisMonth} delta={orderGrowth}
          foot={`${queue.toShip + queue.awaitingOtp} still to fulfil`} />
        <Stat label="Average order" value={inr(metrics.aov)}
          foot={`${metrics.uniqueBuyers} buyer${metrics.uniqueBuyers === 1 ? "" : "s"}, ${metrics.repeatBuyers} returning`} />
        <Stat label="Your share" value={inr(metrics.netThisMonth)}
          foot={metrics.isPro ? "Full payout · Pro plan"
            : `After ${inr(metrics.commissionThisMonth)} commission`} />
      </section>

      {/* ---- Chart + orders / right rail ---- */}
      <div className="grid gap-5 xl:grid-cols-[1.62fr_1fr]">
        <div className="flex flex-col gap-5">
          <Card title="Sales, last 30 days" hint="Paid and completed orders only" testId="home-chart">
            <Sparkline points={daily} />
          </Card>

          <Card
            title="Latest orders"
            right={
              <button type="button" onClick={() => onNav("orders")} className="text-xs font-bold text-[#C43D00] hover:underline">
                See all {metrics.totalOrders}
              </button>
            }
          >
            {orders.length === 0 ? (
              <p className="py-4 text-center text-xs font-medium text-neutral-400">
                No orders yet. Share your shop link to get the first one.
              </p>
            ) : (
              <div className="-mx-5 -my-1 divide-y divide-neutral-100">
                {orders.slice(0, 5).map((o) => (
                  <Link key={o.order_id} to={`/orders/${o.order_id}`}
                    className="flex min-h-[56px] flex-wrap items-center gap-x-3 gap-y-1.5 px-5 py-2.5 transition-colors hover:bg-neutral-50">
                    <div className="min-w-0 flex-1 basis-[55%]">
                      <div className="truncate text-[13px] font-bold text-[#0A0A0A]">{o.buyerName}</div>
                      <div className="truncate text-[11px] font-medium text-neutral-400">
                        {(o.items || []).map((i) => `${i.title} ×${i.quantity}`).join(", ")}
                      </div>
                    </div>
                    <div className="ml-auto text-[13px] font-extrabold text-[#0A0A0A]">{inr(o.amount)}</div>
                    <div className="basis-full sm:basis-auto sm:order-first"><StatusPill status={o.status} /></div>
                  </Link>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-5">
          <Card title="Where your money is" testId="home-money">
            <div className="mk-head text-[32px] font-black leading-none tracking-tight text-[#0A0A0A]">
              {inr(money.heldNet)}
            </div>
            <p className="mt-1.5 text-xs font-medium text-neutral-500">
              Held until each delivery is confirmed, then settled to your bank.
            </p>
            <div className="mt-4 flex flex-col gap-2 border-t border-neutral-100 pt-3.5">
              <div className="flex justify-between text-xs">
                <span className="font-medium text-neutral-500">Collected online</span>
                <span className="font-bold text-[#0A0A0A]">{inr(money.held)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="font-medium text-neutral-500">Commission</span>
                <span className="font-bold text-rose-600">−{inr(money.held - money.heldNet)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="font-medium text-neutral-500">Cash you collected</span>
                <span className="font-bold text-neutral-400">{inr(money.cashCollected)} · kept</span>
              </div>
              <div className="flex justify-between border-t border-neutral-100 pt-2 text-xs">
                <span className="font-medium text-neutral-500">Settled so far</span>
                <span className="font-bold text-emerald-600">{inr(money.settled)}</span>
              </div>
            </div>
          </Card>

          <Card title="Best sellers" hint="This month, by revenue">
            <BarList
              rows={topProducts.map((p) => ({ label: p.title, value: p.revenue, display: inr(p.revenue) }))}
              empty="No sales yet this month."
            />
          </Card>

          <Card
            title="Shop health"
            right={<span className="text-xs font-extrabold text-emerald-600">{healthDone} of {healthItems.length}</span>}
          >
            <div className="flex flex-col gap-2.5">
              {healthItems.map(([label, done]) => (
                <div key={label} className="flex items-center gap-2.5">
                  <span className={`flex h-[17px] w-[17px] shrink-0 items-center justify-center rounded-full border ${
                    done ? "border-emerald-200 bg-emerald-50" : "border-neutral-300 bg-white"}`}>
                    {done && <Check className="h-2.5 w-2.5 text-emerald-600" strokeWidth={4} />}
                  </span>
                  <span className={`text-[12.5px] ${done ? "font-medium text-neutral-500" : "font-bold text-[#0A0A0A]"}`}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

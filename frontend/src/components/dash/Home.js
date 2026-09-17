import { useState } from "react";
import { Link } from "react-router-dom";
import { Truck, KeyRound, AlertTriangle, Check, Landmark, ArrowRight } from "lucide-react";
import { StatusPill } from "@/components/Kit";
import { Card, Stat, Sparkline, BarList, Skeleton, inr } from "./Pieces";
import api from "@/lib/api";
import { RAZORPAY_SIGNUP_URL } from "@/lib/site";

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

/**
 * Razorpay isn't set up on this shop.
 *
 * Two situations, because "your shop is live and nobody can pay" is a
 * different kind of urgent from "there's a step left". It goes at the very
 * top, above the queue, and disappears by itself once the flag is set —
 * nothing here can verify the seller's Razorpay account, so the flag is
 * whatever they told us.
 */
function PaymentsBanner({ live, onConnected }) {
  const [saving, setSaving] = useState(false);

  const markDone = async () => {
    setSaving(true);
    try {
      await api.put("/stores/me", { razorpaySignupDone: true });
      await onConnected?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      data-testid="payments-banner"
      className="flex flex-col gap-3 rounded-2xl border border-[#FFD9C2] bg-[#FFF7ED] p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#FFE3CC]">
          <AlertTriangle className="h-4 w-4 text-[#FF4F00]" />
        </span>
        <div>
          <p className="text-sm font-bold text-[#8A2200]">
            {live
              ? "Your shop is live, but buyers can't check out yet."
              : "Payments not set up — connect Razorpay to start accepting orders on your shop."}
          </p>
          <p className="mt-0.5 text-xs font-medium text-neutral-600">
            Stall Wise uses Razorpay to process payments securely. Cash on delivery keeps working
            while you finish this.
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 self-end sm:self-auto">
        <button
          type="button"
          onClick={markDone}
          disabled={saving}
          data-testid="payments-banner-done"
          className="text-xs font-bold text-neutral-500 underline transition-colors hover:text-[#FF4F00] disabled:opacity-50"
        >
          {saving ? "Saving…" : "Already done"}
        </button>
        <a
          href={RAZORPAY_SIGNUP_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="payments-banner-cta"
          className="inline-flex items-center gap-1.5 rounded-xl bg-[#FF4F00] px-4 py-2.5 text-xs font-bold text-white transition-colors hover:bg-[#E04500]"
        >
          {live ? "Connect Razorpay" : "Set up now"} <ArrowRight className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}

function daysAgo(iso) {
  if (!iso) return null;
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  return d <= 0 ? "today" : d === 1 ? "1 day" : `${d} days`;
}

export default function HomeSection({ summary, loading, error, onRetry, orders, onNav, store, onStoreChange }) {
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

  const { queue, metrics, money, daily, topProducts, health, verification } = summary;
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
    // Two different situations. Until payouts are live the shop cannot take an
    // online payment at all — checkout refuses it rather than hold money with
    // no way to forward it — so the wording has to be blunt about that, and
    // has to stop telling a seller who is waiting on Razorpay to go and do
    // something they have already done.
    // Details saved while Route is off need nothing from the seller at all —
    // calling that "action needed" would send them round in circles.
    const state = queue.bankNeedsAttention ? "fix"
      : queue.bankAwaitingPlatform ? "saved"
      : queue.bankSubmitted ? "verifying"
      : "missing";
    const copy = {
      fix: {
        tag: "Action needed", headline: "Re-enter your bank details", cta: "Fix details",
        note: "Razorpay couldn't accept the details you saved. Until you enter them again your shop can only take cash on delivery.",
      },
      saved: {
        tag: "Saved", headline: "Bank details saved", cta: "View",
        note: "Online payouts aren't switched on for Stall Wise yet. Your account connects automatically once they are — until then your shop takes cash on delivery.",
      },
      verifying: {
        tag: "Being verified", headline: "Bank verification pending", cta: "Check status",
        note: "Razorpay is checking your details. Until that finishes your shop can only take cash on delivery.",
      },
      missing: {
        tag: "Action needed", headline: "Add your bank", cta: "Add bank details",
        note: "Your shop can only take cash on delivery until this is done — online payments are turned off because there is nowhere to send the money.",
      },
    }[state];
    tasks.push(
      <Task key="bank" tone="amber" icon={Landmark}
        tag={copy.tag} headline={copy.headline} note={copy.note} cta={copy.cta}
        onClick={() => onNav("payouts")} />
    );
  }

  const growth = metrics.grossLastMonth > 0
    ? Math.round(((metrics.grossThisMonth - metrics.grossLastMonth) / metrics.grossLastMonth) * 100)
    : null;
  const orderGrowth = metrics.ordersLastMonth > 0
    ? Math.round(((metrics.ordersThisMonth - metrics.ordersLastMonth) / metrics.ordersLastMonth) * 100)
    : null;

  // The badge is earned, so show the distance rather than a bare tick — a
  // checklist row that can only be crossed off after 50 finished orders is
  // discouraging without the count beside it.
  const done = verification?.completedOrders ?? 0;
  const needed = verification?.required ?? 50;
  const healthItems = [
    [verification?.verified
      ? "Verified seller badge earned"
      : `Verified badge — ${done} of ${needed} completed orders`,
     Boolean(verification?.verified)],
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
      {store && store.razorpaySignupDone === false && (
        <PaymentsBanner live={(summary.counts?.liveProducts || 0) > 0} onConnected={onStoreChange} />
      )}

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

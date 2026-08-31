import { Card, Skeleton, inr } from "./Pieces";

/** Payouts: what has settled, what is held, and what you already hold in cash.
 *  Bank onboarding itself stays in the existing RouteSection, passed in as a
 *  child so there is one implementation of that form. */
export default function MoneySection({ summary, loading, children }) {
  if (!loading && !summary) {
    return (
      <div className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 p-10 text-center text-sm font-medium text-neutral-600">
        Couldn&apos;t load this right now. Reload the page to try again.
      </div>
    );
  }
  if (loading || !summary) {
    return <div className="flex flex-col gap-5"><Skeleton className="h-[180px]" /><Skeleton className="h-[300px]" /></div>;
  }
  const { money, metrics, counts } = summary;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-5 xl:grid-cols-3">
        <section className="flex flex-col gap-3 rounded-2xl bg-[#0A0A0A] p-5">
          <span className="text-[11px] font-bold uppercase tracking-[0.06em] text-neutral-400">
            Waiting to reach your bank
          </span>
          <div className="mk-head text-[40px] font-black leading-none tracking-tight text-white">
            {inr(money.heldNet)}
          </div>
          <p className="mt-auto text-[11px] font-medium leading-relaxed text-neutral-400">
            Buyers pay Razorpay, which routes your share to your account once each
            delivery is confirmed with the buyer&apos;s code.
          </p>
        </section>

        <Card title="Still to be delivered">
          <div className="mk-head text-3xl font-black leading-none tracking-tight text-[#0A0A0A]">
            {inr(money.held)}
          </div>
          <div className="mt-4 flex flex-col gap-2.5 border-t border-neutral-100 pt-3.5">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-neutral-500">{counts.byStatus.paid} to ship</span>
              <span className="font-bold text-[#0A0A0A]">{inr(summary.queue.toShipValue)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="font-medium text-neutral-500">{counts.byStatus.shipped} out for delivery</span>
              <span className="font-bold text-[#0A0A0A]">{inr(Math.max(0, money.held - summary.queue.toShipValue))}</span>
            </div>
            {money.disputedValue > 0 && (
              <div className="flex justify-between border-t border-neutral-100 pt-2.5 text-xs">
                <span className="font-medium text-neutral-500">{counts.byStatus.disputed} disputed — on hold</span>
                <span className="font-bold text-rose-600">{inr(money.disputedValue)}</span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Cash you collected">
          <div className="mk-head text-3xl font-black leading-none tracking-tight text-[#0A0A0A]">
            {inr(money.cashCollected)}
          </div>
          <p className="mt-3 text-xs font-medium leading-relaxed text-neutral-500">
            You already hold this. Nothing settles to your bank for cash-on-delivery orders.
          </p>
          <div className="mt-auto flex justify-between border-t border-neutral-100 pt-3.5 text-xs">
            <span className="font-medium text-neutral-500">Commission owed on it</span>
            <span className="font-bold text-rose-600">{inr(money.cashCommissionOwed)}</span>
          </div>
        </Card>
      </div>

      <section className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <div>{children}</div>
        <Card title="Settled to date" hint="Completed online orders">
          <div className="mk-head text-3xl font-black leading-none tracking-tight text-emerald-600">
            {inr(money.settled)}
          </div>
          <div className="mt-4 flex flex-col gap-2.5 border-t border-neutral-100 pt-3.5">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-neutral-500">Your plan</span>
              <span className="font-bold text-[#0A0A0A]">{metrics.isPro ? "Stall Wise Pro" : "Free"}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="font-medium text-neutral-500">Commission rate</span>
              <span className="font-bold text-[#0A0A0A]">{Math.round(metrics.commissionRate * 100)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="font-medium text-neutral-500">Commission this month</span>
              <span className="font-bold text-rose-600">{inr(metrics.commissionThisMonth)}</span>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}

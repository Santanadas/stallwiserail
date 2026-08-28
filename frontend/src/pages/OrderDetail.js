import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Truck, PackageCheck, AlertTriangle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Panel, Field, Btn, StatusPill, Note } from "@/components/Kit";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

function Countdown({ expires }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const ms = new Date(expires).getTime() - now;
  if (ms <= 0) return <b data-testid="window-closed" className="text-[#8A2200]">Window closed</b>;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return (
    <b data-testid="window-countdown" className="mk-head text-2xl font-black tracking-tighter text-[#FF4F00]">
      {m}m {s}s
    </b>
  );
}

export default function OrderDetail() {
  const { orderId } = useParams();
  const [order, setOrder] = useState(null);
  const [otp, setOtp] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useDocumentMeta({
    title: `Order ${orderId} | Marketo`,
    description: "Manage this Marketo order: shipping, delivery OTP and dispute window.",
    path: `/orders/${orderId}`,
  });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/orders/${orderId}`);
      setOrder(data);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [orderId]);
  useEffect(() => { load(); }, [load]);

  const act = async (fn) => {
    setErr(""); setMsg("");
    try { await fn(); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { load(); }
  };

  const shell = (children) => (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]">
      <header className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-3.5 md:px-8">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter">
            MARKETO<span className="text-[#FF4F00]">.</span>
          </Link>
          <Link
            to="/dashboard"
            data-testid="back-to-dashboard"
            className="inline-flex items-center gap-1.5 text-sm font-bold transition-colors hover:text-[#FF4F00]"
          >
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-10 md:px-8 md:py-14">{children}</main>
    </div>
  );

  if (err && !order) return shell(<Note tone="error" data-testid="order-error">{err}</Note>);
  if (!order) return shell(<p className="text-sm text-[#525252]">Loading…</p>);

  return shell(
    <div data-testid="order-detail" className="space-y-8">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">Order</p>
        <h1 className="mk-head break-all text-3xl font-black tracking-tighter sm:text-4xl">{order.order_id}</h1>
        <div className="mt-4">
          <StatusPill status={order.status} data-testid="detail-status" />
        </div>
      </div>

      <Panel title="Summary" testId="order-summary-panel">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-bold uppercase tracking-widest text-[#525252]">Buyer</dt>
            <dd className="mt-1 text-sm">{order.buyerName} <span className="text-[#525252]">({order.buyerEmail})</span></dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-widest text-[#525252]">Total</dt>
            <dd className="mk-head mt-1 text-2xl font-black tracking-tighter">₹{order.amount}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-bold uppercase tracking-widest text-[#525252]">Items</dt>
            <dd className="mt-2">
              <ul className="divide-y divide-[#E5E5E5] border-y border-[#E5E5E5]">
                {order.items.map((i, idx) => (
                  <li key={idx} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5 text-sm">
                    <span>
                      <b>{i.title}</b> × {i.quantity}
                      {Object.keys(i.optionSelections || {}).length ? (
                        <span className="text-[#525252]">
                          {" "}({Object.entries(i.optionSelections).map(([k, v]) => `${k}: ${v}`).join(", ")})
                        </span>
                      ) : null}
                    </span>
                    <span className="font-bold">₹{i.unitPrice}</span>
                  </li>
                ))}
              </ul>
            </dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-widest text-[#525252]">Acceptance window</dt>
            <dd className="mt-1 text-sm">{order.acceptanceWindowMinutes} min</dd>
          </div>
        </dl>
      </Panel>

      {(order.status === "paid" ||
        order.status === "shipped" ||
        order.status === "delivered_pending_otp" ||
        order.status === "delivered_confirmed") && (
        <Panel title="Delivery" testId="order-actions-panel">
          <div className="flex flex-wrap gap-3">
            {order.status === "paid" && (
              <Btn variant="primary" data-testid="ship-btn" onClick={() => act(() => api.post(`/orders/${order.order_id}/ship`))}>
                <Truck className="h-4 w-4" /> Mark shipped (issues OTP to buyer)
              </Btn>
            )}
            {order.status === "shipped" && (
              <Btn variant="dark" data-testid="out-for-delivery-btn" onClick={() => act(() => api.post(`/orders/${order.order_id}/out-for-delivery`))}>
                Out for delivery
              </Btn>
            )}
          </div>

          {(order.status === "shipped" || order.status === "delivered_pending_otp") && (
            <div className="mt-5 border-2 border-dashed border-neutral-300 p-4 sm:p-5">
              <p className="text-sm text-[#525252]">Ask the buyer for the code they received by email.</p>
              <div className="mt-3 flex flex-wrap items-end gap-3">
                <div className="w-44">
                  <Field
                    label="Buyer OTP"
                    data-testid="otp-input"
                    placeholder="6 digits"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    className="mk-head text-lg tracking-[0.3em]"
                  />
                </div>
                <Btn
                  variant="primary"
                  data-testid="confirm-delivery-btn"
                  onClick={() => act(async () => { await api.post(`/orders/${order.order_id}/confirm-delivery`, { otp }); setMsg("Delivery confirmed"); })}
                >
                  <PackageCheck className="h-4 w-4" /> Confirm delivery
                </Btn>
              </div>
              {order.otpLocked && (
                <div className="mt-3"><Note tone="error" data-testid="otp-locked">OTP locked (too many attempts)</Note></div>
              )}
              <p className="mt-3 text-xs font-bold uppercase tracking-widest text-neutral-500">
                Attempts: {order.otpAttempts}/5
              </p>
            </div>
          )}

          {order.status === "delivered_confirmed" && order.windowExpiresAt && (
            <div className="mt-5 border-2 border-[#0A0A0A] bg-[#FAFAFA] p-5" data-testid="acceptance-window">
              <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">Dispute window closes in</p>
              <div className="mt-1"><Countdown expires={order.windowExpiresAt} /></div>
              <p className="mt-2 text-sm text-[#525252]">Once this hits zero the order is final and no refund can be requested.</p>
            </div>
          )}
        </Panel>
      )}

      {order.disputeRaised && (
        <div className="border-2 border-[#0A0A0A] bg-[#FFE9E0] p-5" data-testid="dispute-box">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#8A2200]">
            <AlertTriangle className="h-4 w-4" /> Dispute raised
          </p>
          <p className="mt-2 text-sm text-[#8A2200]">{order.disputeReason}</p>
        </div>
      )}

      {msg && <Note tone="success">{msg}</Note>}
      {err && <Note tone="error" data-testid="detail-error">{err}</Note>}
    </div>
  );
}

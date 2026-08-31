import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, Truck, Package, ShieldAlert, Clock, KeyRound, CreditCard, Copy, Check } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Btn, StatusPill } from "@/components/Kit";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const STEPS = [
  { key: "placed", label: "Placed", icon: Package },
  { key: "paid", label: "Paid", icon: CreditCard },
  { key: "shipped", label: "Shipped", icon: Truck },
  { key: "delivered", label: "Delivered", icon: CheckCircle2 },
];
const ORDER = ["placed", "paid", "shipped", "delivered", "completed"];

function useCountdown(iso) {
  const [left, setLeft] = useState("");
  useEffect(() => {
    if (!iso) return;
    const tick = () => {
      const ms = new Date(iso).getTime() - Date.now();
      if (ms <= 0) { setLeft("00:00:00"); return; }
      const h = String(Math.floor(ms / 3.6e6)).padStart(2, "0");
      const m = String(Math.floor((ms % 3.6e6) / 6e4)).padStart(2, "0");
      const s = String(Math.floor((ms % 6e4) / 1000)).padStart(2, "0");
      setLeft(`${h}:${m}:${s}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [iso]);
  return left;
}

export default function BuyerOrder() {
  const { orderId } = useParams();
  const [params] = useSearchParams();
  const email = params.get("email") || "";
  const [order, setOrder] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [reason, setReason] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  useDocumentMeta({ title: "Track your order | Stall Wise", description: "Track your Stall Wise order and confirm delivery.", path: `/order/${orderId}` });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/order/${orderId}`, { params: { email } });
      setOrder(data);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [orderId, email]);
  useEffect(() => { load(); }, [load]);

  const countdown = useCountdown(order?.status === "delivered" ? order?.windowExpiresAt : null);

  const pay = async () => {
    setErr(""); setMsg(""); setBusy(true);
    try {
      if (!order.razorpayOrderId || !window.Razorpay) {
        setErr("Payment is not available for this order right now.");
        setBusy(false);
        return;
      }
      const rzp = new window.Razorpay({
        key: order.razorpayKeyId,
        order_id: order.razorpayOrderId,
        amount: Math.round(order.amount * 100),
        currency: "INR",
        name: "Stall Wise",
        description: `Order ${order.order_id}`,
        prefill: { name: order.buyerName, email: order.buyerEmail, contact: order.buyerPhone || "" },
        theme: { color: "#FF4F00" },
        modal: { ondismiss: () => setBusy(false) },
        handler: async (res) => {
          try {
            await api.post(`/orders/${orderId}/verify-payment`, {
              razorpay_order_id: res.razorpay_order_id,
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_signature: res.razorpay_signature,
            });
            setMsg("Payment confirmed.");
          } catch (e) {
            setMsg("Payment received — confirming shortly.");
          } finally {
            setBusy(false);
            load();
          }
        },
      });
      rzp.on("payment.failed", (r) => { setErr(r.error?.description || "Payment failed."); setBusy(false); });
      rzp.open();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); setBusy(false); }
  };

  const dispute = async () => {
    setErr(""); setMsg(""); setBusy(true);
    try {
      await api.post(`/order/${orderId}/dispute`, { email, reason });
      setMsg("Dispute raised. The seller has been notified.");
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const copyOtp = () => { navigator.clipboard?.writeText(order.otp); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  useEffect(() => {
    if (order && order.status === "placed" && !window.Razorpay) {
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      document.body.appendChild(s);
    }
  }, [order]);

  if (err && !order) return (
    <div className="mk flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FAFAFA] px-6 text-center" data-testid="buyer-error">
      <Package className="h-10 w-10 text-neutral-300" />
      <p className="mk-head text-2xl font-black tracking-tighter">Order not found</p>
      <p className="max-w-sm text-sm text-[#525252]">{err}</p>
    </div>
  );
  if (!order) return <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA] text-sm text-[#525252]">Loading…</div>;

  const curIdx = ORDER.indexOf(order.status);

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="buyer-order">
      <header className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-5 py-3.5">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter">STALL WISE<span className="text-[#FF4F00]">.</span></Link>
          <StatusPill status={order.status} data-testid="buyer-status" />
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 py-10 md:py-14">
        <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">Order</p>
        <h1 className="mk-head break-all text-3xl font-black tracking-tighter sm:text-4xl" data-testid="buyer-order-id">{order.order_id}</h1>

        {/* Progress tracker */}
        <div className="mt-8 border-2 border-[#0A0A0A] bg-white p-6 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]">
          {order.status === "disputed" ? (
            <div className="flex items-center gap-3 text-[#8A0000]" data-testid="buyer-disputed">
              <ShieldAlert className="h-6 w-6" />
              <div><p className="font-bold">Dispute raised</p><p className="text-sm text-[#525252]">{order.disputeReason}</p></div>
            </div>
          ) : (
            <ol className="flex items-center justify-between">
              {STEPS.map((s, i) => {
                const stepIdx = ORDER.indexOf(s.key);
                const done = curIdx >= stepIdx || (s.key === "delivered" && order.status === "completed");
                const Icon = s.icon;
                return (
                  <li key={s.key} className="flex flex-1 flex-col items-center gap-2 text-center">
                    <div className={`flex h-11 w-11 items-center justify-center border-2 border-[#0A0A0A] ${done ? "bg-[#FF4F00] text-white" : "bg-white text-neutral-300"}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider ${done ? "text-[#0A0A0A]" : "text-neutral-400"}`}>{s.label}</span>
                  </li>
                );
              })}
            </ol>
          )}
        </div>

        {/* Items */}
        <div className="mt-6 border-2 border-[#0A0A0A] bg-white">
          <div className="border-b-2 border-[#0A0A0A] bg-[#FAFAFA] px-5 py-3"><h2 className="mk-head text-base font-extrabold uppercase tracking-widest">Summary</h2></div>
          <div className="p-5">
            <ul className="divide-y divide-[#E5E5E5]">
              {order.items.map((i, idx) => (
                <li key={idx} className="flex items-center justify-between py-2.5 text-sm">
                  <span>{i.title} <span className="text-[#525252]">×{i.quantity}</span>{Object.keys(i.optionSelections || {}).length > 0 && <span className="ml-2 text-[#525252]">{Object.values(i.optionSelections).join(", ")}</span>}</span>
                  <span className="font-bold">₹{i.unitPrice * i.quantity}</span>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex items-center justify-between border-t-2 border-[#0A0A0A] pt-3">
              <span className="text-sm font-bold uppercase tracking-widest text-[#525252]">Total</span>
              <span className="mk-head text-2xl font-black tracking-tighter">₹{order.amount}</span>
            </div>
          </div>
        </div>

        {/* Pay */}
        {order.status === "placed" && (
          <div className="mt-6">
            <Btn variant="primary" data-testid="buyer-pay-btn" onClick={pay} disabled={busy}>
              <CreditCard className="h-4 w-4" /> Pay with Razorpay
            </Btn>
          </div>
        )}

        {/* Delivery code */}
        {order.otp && (
          <div className="mt-6 border-2 border-[#0A0A0A] bg-[#FFF4E0] p-6" data-testid="buyer-otp-box">
            <div className="flex items-center gap-2 text-[#7A4A00]"><KeyRound className="h-5 w-5" /><span className="text-xs font-bold uppercase tracking-widest">Your delivery code</span></div>
            <div className="mt-3 flex items-center gap-4">
              <span className="mk-head text-4xl font-black tracking-[0.25em]" data-testid="buyer-otp">{order.otp}</span>
              <button onClick={copyOtp} data-testid="buyer-otp-copy" aria-label="Copy code" className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5">
                {copied ? <><Check className="h-3.5 w-3.5" /> Copied</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
              </button>
            </div>
            <p className="mt-3 text-sm text-[#7A4A00]">Share this code with the seller only at handover so they can confirm delivery.</p>
          </div>
        )}

        {/* Dispute window */}
        {order.status === "delivered" && order.windowExpiresAt && (
          <div className="mt-6 border-2 border-[#0A0A0A] bg-white p-6" data-testid="buyer-dispute-section">
            <div className="flex items-center gap-2 text-[#525252]"><Clock className="h-5 w-5" /><span className="text-xs font-bold uppercase tracking-widest">Acceptance window</span></div>
            <p className="mk-head mt-2 text-3xl font-black tracking-tighter" data-testid="buyer-countdown">{countdown}</p>
            <p className="mt-2 text-sm leading-relaxed text-[#525252]">Something wrong with your order? Raise a dispute before the window closes. No refunds are possible after it ends.</p>
            <div className="mt-4 space-y-3">
              <input data-testid="dispute-reason" placeholder="What went wrong?" value={reason || ""} onChange={(e) => setReason(e.target.value)} className="w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#FF4F00]" />
              <Btn variant="danger" data-testid="dispute-btn" onClick={dispute} disabled={busy || !reason.trim()}><ShieldAlert className="h-4 w-4" /> Raise dispute</Btn>
            </div>
          </div>
        )}

        {order.status === "completed" && (
          <div className="mt-6 border-2 border-[#0A0A0A] bg-[#E6F6EC] p-6" data-testid="buyer-completed">
            <div className="flex items-center gap-2 text-[#0B5227]"><CheckCircle2 className="h-5 w-5" /><span className="font-bold">Order completed</span></div>
            <p className="mt-2 text-sm text-[#0B5227]">The acceptance window has closed. Thanks for shopping on Stall Wise.</p>
          </div>
        )}

        {msg && <p className="mt-6 border-2 border-[#0A0A0A] bg-[#E6F6EC] px-4 py-2.5 text-sm font-medium text-[#0B5227]" data-testid="buyer-msg">{msg}</p>}
        {err && <p className="mt-6 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-4 py-2.5 text-sm font-medium text-[#8A2200]" data-testid="buyer-msg-error">{err}</p>}
      </main>
    </div>
  );
}

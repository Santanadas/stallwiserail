import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Trash2, ShoppingBag, Minus, Plus, ArrowRight, CreditCard, Banknote } from "lucide-react";

const field =
  "mt-1.5 w-full min-h-[44px] border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-base outline-none focus:border-[#FF4F00] sm:text-sm";
const labelText = "text-xs font-bold uppercase tracking-widest text-[#525252]";

const PAY_LABELS = {
  online: { label: "Pay online", hint: "UPI · Card · Netbanking · Wallet", Icon: CreditCard },
  cod: { label: "Cash on delivery", hint: "Pay the seller at handover", Icon: Banknote },
};

export default function CartDrawer({
  open,
  onClose,
  cart,
  setQty,
  removeItem,
  cartTotal,
  deliveryFee = 0,
  freeDeliveryAbove = null,
  buyer,
  setBuyer,
  checkout,
  placing,
  err,
  allowedPayments = ["online"],
  payMethod = "online",
  setPayMethod,
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const phoneOk = (buyer.buyerPhone || "").replace(/\D/g, "").length >= 8;
  const noSharedMethod = cart.length > 0 && allowedPayments.length === 0;
  const canPay =
    !placing && buyer.buyerName.trim() && buyer.buyerEmail.trim() && phoneOk && cart.length > 0 && !noSharedMethod;
  // Mirrors delivery_for() on the server: free once the threshold is met, and
  // the threshold is inclusive because "free delivery above ₹1,500" reads to a
  // buyer as "spend ₹1,500 and it is free". If these two ever disagree the
  // buyer is quoted one number and charged another, so they have to match.
  const subtotal = Number(cartTotal) || 0;
  const delivery =
    deliveryFee > 0 && !(freeDeliveryAbove != null && subtotal >= freeDeliveryAbove)
      ? deliveryFee
      : 0;
  const grandTotal = subtotal + delivery;
  const awayFromFree =
    deliveryFee > 0 && freeDeliveryAbove != null && subtotal < freeDeliveryAbove
      ? freeDeliveryAbove - subtotal
      : 0;

  const payCta =
    payMethod === "cod" ? `Place order · ₹${grandTotal}` : `Pay ₹${grandTotal}`;

  return createPortal(
    <div className="mk fixed inset-0 z-[100] flex justify-end" data-testid="cart-drawer">
      <div className="absolute inset-0 bg-neutral-900/40" onClick={onClose} />

      <aside className="relative flex h-full w-full max-w-md flex-col border-l-2 border-[#0A0A0A] bg-[#FAFAFA] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b-2 border-[#0A0A0A] bg-white px-4 py-3.5">
          <div className="flex items-center gap-2">
            <ShoppingBag className="h-5 w-5" />
            <h2 className="mk-head text-base font-extrabold uppercase tracking-widest">Your cart</h2>
            <span className="border border-[#0A0A0A] bg-[#FF4F00] px-1.5 text-xs font-bold text-white">
              {cart.length}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close cart"
            className="p-1.5 text-neutral-500 transition-colors hover:text-[#0A0A0A]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {cart.length === 0 ? (
            <div className="mt-16 text-center" data-testid="cart-empty">
              <ShoppingBag className="mx-auto h-9 w-9 text-neutral-300" />
              <p className="mt-3 text-sm text-[#525252]">Your cart is empty.</p>
              <button
                type="button"
                onClick={onClose}
                className="mt-4 border-2 border-[#0A0A0A] bg-white px-4 py-2 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5"
              >
                Keep shopping
              </button>
            </div>
          ) : (
            <ul data-testid="cart-list" className="space-y-3">
              {cart.map((c, i) => (
                <li key={i} className="border-2 border-[#0A0A0A] bg-white p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-bold leading-snug">{c.title}</p>
                      {Object.keys(c.optionSelections || {}).length > 0 && (
                        <p className="mt-0.5 text-xs text-[#525252]">
                          {Object.values(c.optionSelections).join(" · ")}
                        </p>
                      )}
                    </div>
                    <button
                      data-testid={`cart-remove-${i}`}
                      onClick={() => removeItem(i)}
                      aria-label="Remove item"
                      className="shrink-0 p-1 text-[#8A2200] transition-colors hover:text-[#FF4F00]"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <div className="flex items-center border-2 border-[#0A0A0A]">
                      <button
                        type="button"
                        aria-label="Decrease quantity"
                        onClick={() => setQty(i, c.quantity - 1)}
                        className="flex h-8 w-8 items-center justify-center hover:bg-[#FAFAFA]"
                      >
                        <Minus className="h-3.5 w-3.5" />
                      </button>
                      <span data-testid={`cart-qty-${i}`} className="min-w-[2rem] text-center text-sm font-bold">
                        {c.quantity}
                      </span>
                      <button
                        type="button"
                        aria-label="Increase quantity"
                        onClick={() => setQty(i, c.quantity + 1)}
                        className="flex h-8 w-8 items-center justify-center hover:bg-[#FAFAFA]"
                      >
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <span className="mk-head text-base font-black tracking-tighter">
                      ₹{(c.unitPrice || 0) * c.quantity}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Checkout */}
        {cart.length > 0 && (
          <div className="border-t-2 border-[#0A0A0A] bg-white px-4 py-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold text-[#525252]">Subtotal</span>
              <span className="font-bold" data-testid="cart-subtotal">₹{subtotal}</span>
            </div>
            <div className="mt-1 flex items-center justify-between text-sm">
              <span className="font-semibold text-[#525252]">Delivery</span>
              <span className="font-bold" data-testid="cart-delivery">
                {delivery > 0 ? `₹${delivery}` : "Free"}
              </span>
            </div>
            {awayFromFree > 0 && (
              <p className="mt-1.5 text-xs font-semibold text-[#C43D00]">
                Add ₹{awayFromFree} more for free delivery
              </p>
            )}
            <div className="mt-2.5 flex items-center justify-between border-t border-neutral-200 pt-2.5">
              <span className={labelText}>Total</span>
              <span className="mk-head text-2xl font-black tracking-tighter" data-testid="cart-total">
                ₹{grandTotal}
              </span>
            </div>

            {/* Payment method */}
            <div className="mt-4">
              <span className={labelText}>Payment</span>
              {noSharedMethod ? (
                <p className="mt-1.5 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-3 py-2 text-xs font-medium text-[#8A2200]">
                  These items don't share a payment method — order the cash-only items separately.
                </p>
              ) : (
                <div className="mt-1.5 grid gap-2" data-testid="payment-methods">
                  {allowedPayments.map((m) => {
                    const { label, hint, Icon } = PAY_LABELS[m] || PAY_LABELS.online;
                    const on = payMethod === m;
                    const only = allowedPayments.length === 1;
                    return (
                      <button
                        key={m}
                        type="button"
                        data-testid={`pay-${m}`}
                        onClick={() => setPayMethod?.(m)}
                        aria-pressed={on}
                        className={`flex items-center gap-3 border-2 px-3 py-2.5 text-left transition-colors ${
                          on ? "border-[#0A0A0A] bg-[#FFF4E0]" : "border-neutral-300 bg-white hover:border-[#0A0A0A]"
                        }`}
                      >
                        <Icon className={`h-4 w-4 shrink-0 ${on ? "text-[#FF4F00]" : "text-neutral-400"}`} />
                        <span className="min-w-0">
                          <span className="block text-sm font-bold">{label}</span>
                          <span className="block text-xs text-[#525252]">{hint}</span>
                        </span>
                        {!only && (
                          <span
                            className={`ml-auto h-3.5 w-3.5 shrink-0 rounded-full border-2 border-[#0A0A0A] ${on ? "bg-[#FF4F00]" : "bg-white"}`}
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="mt-4 space-y-3">
              <label className="block">
                <span className={labelText}>Your name</span>
                <input
                  data-testid="buyer-name"
                  value={buyer.buyerName || ""}
                  onChange={(e) => setBuyer({ ...buyer, buyerName: e.target.value })}
                  placeholder="Full name"
                  className={field}
                />
              </label>
              <label className="block">
                <span className={labelText}>Your email</span>
                <input
                  data-testid="buyer-email"
                  type="email"
                  value={buyer.buyerEmail || ""}
                  onChange={(e) => setBuyer({ ...buyer, buyerEmail: e.target.value })}
                  placeholder="you@example.com"
                  className={field}
                />
              </label>
              <label className="block">
                <span className={labelText}>Your phone</span>
                <input
                  data-testid="buyer-phone"
                  inputMode="tel"
                  value={buyer.buyerPhone || ""}
                  onChange={(e) => setBuyer({ ...buyer, buyerPhone: e.target.value })}
                  placeholder="10-digit mobile number"
                  className={field}
                />
              </label>
            </div>

            <button
              data-testid="checkout-btn"
              onClick={checkout}
              disabled={!canPay}
              className="mt-4 inline-flex w-full min-h-[48px] items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
            >
              {placing ? "Processing…" : <>{payCta} <ArrowRight className="h-4 w-4" /></>}
            </button>
            <p className="mt-2 text-center text-xs text-[#525252]">
              {payMethod === "cod"
                ? "Pay the seller in cash when your order is delivered."
                : "Secure payment via Razorpay — money goes straight to the seller."}
            </p>
            {err && (
              <p
                className="mt-3 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-3 py-2 text-sm font-medium text-[#8A2200]"
                data-testid="checkout-error"
              >
                {err}
              </p>
            )}
          </div>
        )}
      </aside>
    </div>,
    document.body
  );
}

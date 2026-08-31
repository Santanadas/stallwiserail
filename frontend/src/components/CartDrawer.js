import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Trash2, ShoppingBag, Minus, Plus, ArrowRight } from "lucide-react";

const field =
  "mt-1.5 w-full min-h-[44px] border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-base outline-none focus:border-[#FF4F00] sm:text-sm";
const labelText = "text-xs font-bold uppercase tracking-widest text-[#525252]";

export default function CartDrawer({
  open,
  onClose,
  cart,
  setQty,
  removeItem,
  cartTotal,
  buyer,
  setBuyer,
  checkout,
  placing,
  err,
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
  const canPay = !placing && buyer.buyerName.trim() && buyer.buyerEmail.trim() && phoneOk && cart.length > 0;

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
            <div className="flex items-center justify-between">
              <span className={labelText}>Total</span>
              <span className="mk-head text-2xl font-black tracking-tighter" data-testid="cart-total">
                ₹{cartTotal}
              </span>
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
              {placing ? "Processing…" : <>Pay ₹{cartTotal} <ArrowRight className="h-4 w-4" /></>}
            </button>
            <p className="mt-2 text-center text-xs text-[#525252]">
              Secure payment via Razorpay — money goes straight to the seller.
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

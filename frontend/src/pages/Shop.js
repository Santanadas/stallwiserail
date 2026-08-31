import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ShoppingBag, Store, ArrowRight, Package, Share2, Check } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import CartDrawer from "@/components/CartDrawer";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

function initials(name) {
  return (name || "S").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export default function Shop() {
  const { storeSlug } = useParams();
  const navigate = useNavigate();
  const [shop, setShop] = useState(null);
  const [err, setErr] = useState("");
  const [selections, setSelections] = useState({});
  const [cart, setCart] = useState([]);
  const [buyer, setBuyer] = useState({ buyerName: "", buyerEmail: "", buyerPhone: "" });
  const [placing, setPlacing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [payMethod, setPayMethod] = useState("online");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/shop/${storeSlug}`);
      setShop(data);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [storeSlug]);
  useEffect(() => { load(); }, [load]);

  const shareShop = async () => {
    const url = `https://stallwise.in/${shop?.store?.slug || storeSlug}`;
    const title = `${shop?.store?.name || "Store"} on Stall Wise`;
    if (navigator.share) {
      try {
        await navigator.share({ title, text: `Check out ${shop?.store?.name || "this shop"} on Stall Wise!`, url });
        return;
      } catch {
        // User cancelled or fallback to clipboard
      }
    }
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const pickOption = (pid, group, label) =>
    setSelections({ ...selections, [pid]: { ...(selections[pid] || {}), [group]: label } });

  const unitPrice = (p) => {
    const sel = selections[p.product_id] || {};
    let price = p.price;
    (p.optionGroups || []).forEach((g) => {
      if (!g?.name) return;
      const opt = (g.options || []).find((o) => o?.label === sel[g.name]);
      if (opt) price += opt.priceDelta || 0;
    });
    return price;
  };

  const addToCart = (p) => {
    const sel = selections[p.product_id] || {};
    for (const g of p.optionGroups || []) {
      if (!g?.name) continue;
      if (!sel[g.name]) { setErr(`Pick a ${g.name} for ${p.title}`); return; }
      const opt = (g.options || []).find((o) => o?.label === sel[g.name]);
      if (opt && opt.stock === 0) { setErr(`${g.name} ${opt.label} is out of stock`); return; }
    }
    setErr("");
    setCart([...cart, {
      productId: p.product_id,
      title: p.title,
      quantity: 1,
      optionSelections: sel,
      unitPrice: unitPrice(p),
      paymentMethods: (p.paymentMethods && p.paymentMethods.length) ? p.paymentMethods : ["online"],
    }]);
    setCartOpen(true);
  };

  const removeItem = (i) => setCart(cart.filter((_, idx) => idx !== i));
  const setQty = (i, q) => {
    if (q < 1) return removeItem(i);
    setCart(cart.map((c, idx) => (idx === i ? { ...c, quantity: Math.min(q, 999) } : c)));
  };
  const cartTotal = cart.reduce((s, c) => s + (c.unitPrice || 0) * c.quantity, 0);

  // A payment method is offered only if every item in the cart accepts it.
  const allowedPayments = cart.reduce(
    (acc, c) => acc.filter((m) => (c.paymentMethods || ["online"]).includes(m)),
    ["online", "cod"]
  );

  useEffect(() => {
    if (allowedPayments.length && !allowedPayments.includes(payMethod)) {
      setPayMethod(allowedPayments[0]);
    }
  }, [allowedPayments, payMethod]);

  const isSoldOut = (p) => {
    if (p.stock === 0) return true;
    if ((p.optionGroups || []).length && p.optionGroups.every((g) => (g.options || []).every((o) => o.stock === 0))) return true;
    return false;
  };

  const loadRazorpay = () =>
    new Promise((res) => {
      if (window.Razorpay) return res(true);
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.onload = () => res(true);
      s.onerror = () => res(false);
      document.body.appendChild(s);
    });

  const checkout = async () => {
    setErr("");
    setPlacing(true);
    const email = buyer.buyerEmail.trim();
    try {
      const { data } = await api.post("/orders", {
        storeSlug,
        buyerName: buyer.buyerName.trim(),
        buyerEmail: email,
        buyerPhone: buyer.buyerPhone.replace(/\D/g, ""),
        paymentMethod: payMethod,
        items: cart.map((c) => ({ productId: c.productId, quantity: c.quantity, optionSelections: c.optionSelections })),
      });

      const orderId = data.orderId;
      const goToOrder = () => navigate(`/order/${orderId}?email=${encodeURIComponent(email)}`);

      // Cash on delivery: nothing to charge now — the seller collects at handover.
      if (payMethod === "cod" || !data.razorpayOrderId) {
        goToOrder();
        return;
      }

      const ok = await loadRazorpay();
      if (!ok || !window.Razorpay) {
        setErr("Could not load the payment window. Your order was saved — open it to pay.");
        goToOrder();
        return;
      }

      const rzp = new window.Razorpay({
        key: data.razorpayKeyId,
        order_id: data.razorpayOrderId,
        amount: Math.round((data.amount || cartTotal) * 100),
        currency: "INR",
        name: shop?.store?.name || "Stall Wise",
        description: `Order ${orderId}`,
        prefill: { name: buyer.buyerName.trim(), email, contact: buyer.buyerPhone.replace(/\D/g, "") },
        theme: { color: "#FF4F00" },
        modal: { ondismiss: () => { setPlacing(false); goToOrder(); } },
        handler: async (res) => {
          try {
            await api.post(`/orders/${orderId}/verify-payment`, {
              razorpay_order_id: res.razorpay_order_id,
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_signature: res.razorpay_signature,
            });
          } catch {
            // Payment went through at Razorpay; the webhook will reconcile.
          } finally {
            goToOrder();
          }
        },
      });
      rzp.on("payment.failed", (r) => {
        setErr(r.error?.description || "Payment failed. Your order was saved — open it to try again.");
        setPlacing(false);
      });
      rzp.open();
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail));
      setPlacing(false);
    }
  };

  const productsList = Array.isArray(shop?.products) ? shop.products : [];

  // Schema.org Structured Data for Store & Products
  const shopSchema = shop?.store ? {
    "@context": "https://schema.org",
    "@type": "Store",
    "name": shop.store.name,
    "description": shop.store.bio || `Shop from ${shop.store.name} on Stall Wise`,
    "url": `https://stallwise.in/${shop.store.slug || storeSlug}`,
    "image": shop.seller?.avatar ? fileUrl(shop.seller.avatar) : undefined,
    "makesOffer": productsList.map((p) => ({
      "@type": "Offer",
      "price": p.price,
      "priceCurrency": "INR",
      "availability": p.stock === 0 ? "https://schema.org/OutOfStock" : "https://schema.org/InStock",
      "itemOffered": {
        "@type": "Product",
        "name": p.title,
        "description": p.description || p.title,
        "image": p.image ? fileUrl(p.image) : undefined,
        "offers": {
          "@type": "Offer",
          "price": p.price,
          "priceCurrency": "INR",
          "availability": p.stock === 0 ? "https://schema.org/OutOfStock" : "https://schema.org/InStock",
        },
      },
    })),
  } : null;

  useDocumentMeta({
    title: shop?.store?.name ? `${shop.store.name} | Stall Wise` : "Shop | Stall Wise",
    description: shop?.store?.bio || "Shop directly and pay the seller — zero commission on Stall Wise.",
    path: `/${storeSlug}`,
    schemaData: shopSchema,
    image: shop?.seller?.avatar ? fileUrl(shop.seller.avatar) : undefined,
  });

  if (err && !shop) return (
    <div className="mk flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FAFAFA] px-6 text-center" data-testid="shop-error">
      <Store className="h-10 w-10 text-neutral-300" />
      <p className="mk-head text-2xl font-black tracking-tighter">Shop not found</p>
      <p className="max-w-sm text-sm text-[#525252]">{err}</p>
      <Link to="/" className="mt-2 border-2 border-[#0A0A0A] bg-white px-5 py-2.5 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]">Back to Stall Wise</Link>
    </div>
  );
  if (!shop) return <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA] text-sm text-[#525252]">Loading…</div>;

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] pb-24 text-[#0A0A0A] sm:pb-12" data-testid="shop-page">
      {err && !cartOpen && (
        <div
          className="fixed left-1/2 top-4 z-[110] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-4 py-2.5 text-sm font-medium text-[#8A2200] shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]"
          data-testid="shop-toast"
          onClick={() => setErr("")}
        >
          {err}
        </div>
      )}
      <header className="sticky top-0 z-50 border-b-2 border-[#0A0A0A] bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6 md:px-8 md:py-3.5">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter sm:text-xl">STALL WISE<span className="text-[#FF4F00]">.</span></Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={shareShop}
              aria-label="Share shop"
              className="inline-flex min-h-[40px] items-center gap-1.5 border-2 border-[#0A0A0A] bg-white px-3 py-1.5 text-xs font-bold text-[#0A0A0A] transition-transform hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_rgba(10,10,10,1)] sm:text-sm"
              data-testid="share-shop-btn"
            >
              {copied ? <Check className="h-4 w-4 text-[#0B5227]" /> : <Share2 className="h-4 w-4" />}
              <span>{copied ? "Copied!" : "Share"}</span>
            </button>
            <button
              type="button"
              onClick={() => setCartOpen(true)}
              className="relative inline-flex min-h-[40px] items-center gap-2 border-2 border-[#0A0A0A] bg-white px-3 py-1.5 text-xs font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_rgba(10,10,10,1)] sm:text-sm"
              data-testid="cart-jump"
            >
              <ShoppingBag className="h-4 w-4" /> Cart
              {cart.length > 0 && <span className="ml-1 border border-[#0A0A0A] bg-[#FF4F00] px-1.5 text-xs text-white" data-testid="cart-count">{cart.length}</span>}
            </button>
          </div>
        </div>
      </header>

      {/* Shop banner */}
      <section className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10 md:px-8 md:py-14">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:gap-6">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00] shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] sm:h-24 sm:w-24 sm:shadow-[5px_5px_0px_0px_rgba(10,10,10,1)]" data-testid="shop-avatar">
              {shop.seller?.avatar ? (
                <img src={fileUrl(shop.seller.avatar)} alt={shop.store?.name || "Shop"} className="h-full w-full object-cover" />
              ) : (
                <span className="mk-head text-2xl font-black text-white sm:text-3xl">{initials(shop.store?.name)}</span>
              )}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <h1 data-testid="shop-name" className="mk-head text-3xl font-black leading-tight tracking-tighter sm:text-4xl md:text-5xl">{shop.store?.name || "Shop"}</h1>
              </div>
              <p className="mt-1 text-xs font-medium text-[#525252] sm:text-sm">
                stallwise.in/<span className="font-bold text-[#0A0A0A]">{shop.store?.slug || storeSlug}</span>
              </p>
              {shop.store?.bio && <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#525252] sm:text-base" data-testid="shop-bio">{shop.store.bio}</p>}
            </div>
          </div>
        </div>
      </section>

      {shop.showAds && (
        <div className="mx-auto mt-4 max-w-5xl px-4 sm:px-6 md:px-8">
          <div data-testid="ad-slot" className="border-2 border-dashed border-neutral-300 bg-white px-4 py-3 text-center text-xs font-bold uppercase tracking-widest text-neutral-400">
            Ad slot — this seller is on the free plan
          </div>
        </div>
      )}

      {/* Products */}
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10 md:px-8 md:py-14">
        <div className="mb-6 flex items-baseline justify-between sm:mb-8">
          <h2 className="mk-head text-lg font-extrabold uppercase tracking-widest sm:text-xl">Products</h2>
          <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{productsList.length} items</span>
        </div>

        {productsList.length === 0 ? (
          <div className="border-2 border-[#0A0A0A] bg-white p-8 text-center sm:p-12" data-testid="shop-empty">
            <Package className="mx-auto h-8 w-8 text-neutral-300" />
            <p className="mt-3 text-sm text-[#525252]">This shop hasn't listed any products yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 sm:gap-6">
            {productsList.map((p) => {
              const sold = isSoldOut(p);
              return (
                <div key={p.product_id} data-testid={`shop-product-${p.product_id}`} className="group flex flex-col border-2 border-[#0A0A0A] bg-white transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]">
                  <div className="relative aspect-square overflow-hidden border-b-2 border-[#0A0A0A] bg-[#FAFAFA]">
                    {p.image ? (
                      <img src={fileUrl(p.image)} alt={p.title} className="h-full w-full object-cover" loading="lazy" />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center"><Package className="h-10 w-10 text-neutral-300" /></div>
                    )}
                    {sold && <div className="absolute inset-0 flex items-center justify-center bg-white/70"><span className="border-2 border-[#0A0A0A] bg-white px-3 py-1 text-xs font-black uppercase tracking-widest">Sold out</span></div>}
                  </div>
                  <div className="flex flex-1 flex-col p-4 sm:p-5">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-base font-bold leading-snug">{p.title}</h3>
                      <span className="mk-head shrink-0 text-lg font-black tracking-tighter">₹{unitPrice(p)}</span>
                    </div>
                    {p.description && <p className="mt-2 text-sm leading-relaxed text-[#525252]">{p.description}</p>}
                    {(p.paymentMethods || []).includes("cod") && (
                      <span className="mt-2 inline-block w-fit border border-[#0A0A0A] bg-[#FFF4E0] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                        Cash on delivery
                      </span>
                    )}
                    {p.stock != null && (p.optionGroups || []).length === 0 && (
                      <span data-testid={`stock-${p.product_id}`} className={`mt-2 text-xs font-bold uppercase tracking-wider ${p.stock === 0 ? "text-[#8A2200]" : "text-[#0B5227]"}`}>
                        {p.stock === 0 ? "Out of stock" : `${p.stock} in stock`}
                      </span>
                    )}
                    <div className="mt-4 space-y-3">
                      {(p.optionGroups || []).filter((g) => g && g.name).map((g) => (
                        <div key={g.name}>
                          <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{g.name}</span>
                          <select
                            data-testid={`option-${p.product_id}-${g.name}`}
                            value={(selections[p.product_id] || {})[g.name] || ""}
                            onChange={(e) => pickOption(p.product_id, g.name, e.target.value)}
                            className="mt-1 w-full min-h-[42px] border-2 border-[#0A0A0A] bg-white px-2.5 py-2 text-base outline-none focus:border-[#FF4F00] sm:text-sm"
                          >
                            <option value="">Select</option>
                            {(g.options || []).filter((o) => o && o.label).map((o) => (
                              <option key={o.label} value={o.label} disabled={o.stock === 0}>
                                {o.label}{o.priceDelta ? ` (+₹${o.priceDelta})` : ""}{o.stock === 0 ? " — sold out" : o.stock != null ? ` (${o.stock} left)` : ""}
                              </option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                    <button
                      data-testid={`add-cart-${p.product_id}`}
                      onClick={() => addToCart(p)}
                      disabled={sold}
                      className="mt-5 inline-flex min-h-[44px] items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
                    >
                      {sold ? "Sold out" : <>Add to cart <ShoppingBag className="h-4 w-4" /></>}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </main>

      {/* Floating Sticky Mobile Cart Bar */}
      {cart.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t-2 border-[#0A0A0A] bg-[#0A0A0A] p-3 text-white shadow-2xl sm:hidden">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <span className="text-xs text-neutral-400">{cart.length} {cart.length === 1 ? "item" : "items"}</span>
              <p className="mk-head text-lg font-black text-white">₹{cartTotal}</p>
            </div>
            <button
              type="button"
              onClick={() => setCartOpen(true)}
              className="inline-flex min-h-[42px] items-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-4 py-2 text-xs font-black uppercase tracking-wider text-white"
            >
              Checkout <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      <CartDrawer
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        cart={cart}
        setQty={setQty}
        removeItem={removeItem}
        cartTotal={cartTotal}
        buyer={buyer}
        setBuyer={setBuyer}
        checkout={checkout}
        placing={placing}
        err={err}
        allowedPayments={allowedPayments}
        payMethod={payMethod}
        setPayMethod={setPayMethod}
      />
    </div>
  );
}

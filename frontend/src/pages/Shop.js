import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ShoppingBag, Trash2, Store, ArrowRight, Package } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import { Btn } from "@/components/Kit";
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
  const [buyer, setBuyer] = useState({ buyerName: "", buyerEmail: "" });
  const [placing, setPlacing] = useState(false);

  useDocumentMeta({
    title: shop?.store?.name ? `${shop.store.name} | Marketo` : "Shop | Marketo",
    description: shop?.store?.bio || "Shop directly and pay the seller — zero commission on Marketo.",
    path: `/${storeSlug}`,
  });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/shop/${storeSlug}`);
      setShop(data);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [storeSlug]);
  useEffect(() => { load(); }, [load]);

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
    setCart([...cart, { productId: p.product_id, title: p.title, quantity: 1, optionSelections: sel, unitPrice: unitPrice(p) }]);
  };

  const removeItem = (i) => setCart(cart.filter((_, idx) => idx !== i));
  const cartTotal = cart.reduce((s, c) => s + (c.unitPrice || 0) * c.quantity, 0);

  const isSoldOut = (p) => {
    if (p.stock === 0) return true;
    if ((p.optionGroups || []).length && p.optionGroups.every((g) => (g.options || []).every((o) => o.stock === 0))) return true;
    return false;
  };

  const checkout = async () => {
    setErr("");
    setPlacing(true);
    try {
      const { data } = await api.post("/orders", {
        storeSlug, buyerName: buyer.buyerName, buyerEmail: buyer.buyerEmail,
        items: cart.map((c) => ({ productId: c.productId, quantity: c.quantity, optionSelections: c.optionSelections })),
      });
      navigate(`/order/${data.orderId}?email=${encodeURIComponent(buyer.buyerEmail)}`);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setPlacing(false); }
  };

  if (err && !shop) return (
    <div className="mk flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FAFAFA] px-6 text-center" data-testid="shop-error">
      <Store className="h-10 w-10 text-neutral-300" />
      <p className="mk-head text-2xl font-black tracking-tighter">Shop not found</p>
      <p className="max-w-sm text-sm text-[#525252]">{err}</p>
      <Link to="/" className="mt-2 border-2 border-[#0A0A0A] bg-white px-5 py-2.5 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]">Back to Marketo</Link>
    </div>
  );
  if (!shop) return <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA] text-sm text-[#525252]">Loading…</div>;

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="shop-page">
      <header className="sticky top-0 z-50 border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3.5 md:px-8">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter">MARKETO<span className="text-[#FF4F00]">.</span></Link>
          <a href="#cart" className="relative inline-flex items-center gap-2 border-2 border-[#0A0A0A] bg-white px-3 py-2 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_rgba(10,10,10,1)]" data-testid="cart-jump">
            <ShoppingBag className="h-4 w-4" /> Cart
            {cart.length > 0 && <span className="ml-1 border border-[#0A0A0A] bg-[#FF4F00] px-1.5 text-xs text-white" data-testid="cart-count">{cart.length}</span>}
          </a>
        </div>
      </header>

      {/* Shop banner */}
      <section className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto max-w-5xl px-5 py-10 md:px-8 md:py-14">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
            <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00] shadow-[5px_5px_0px_0px_rgba(10,10,10,1)]" data-testid="shop-avatar">
              {shop.seller?.avatar ? (
                <img src={fileUrl(shop.seller.avatar)} alt={shop.store?.name || "Shop"} className="h-full w-full object-cover" />
              ) : (
                <span className="mk-head text-3xl font-black text-white">{initials(shop.store?.name)}</span>
              )}
            </div>
            <div className="min-w-0">
              <h1 data-testid="shop-name" className="mk-head text-4xl font-black leading-none tracking-tighter sm:text-5xl">{shop.store?.name || "Shop"}</h1>
              <p className="mt-2 text-sm font-medium text-[#525252]">marketo.com/<span className="font-bold text-[#0A0A0A]">{shop.store?.slug || storeSlug}</span></p>
              {shop.store?.bio && <p className="mt-4 max-w-2xl text-base leading-relaxed text-[#525252]" data-testid="shop-bio">{shop.store.bio}</p>}
            </div>
          </div>
        </div>
      </section>

      {shop.showAds && (
        <div className="mx-auto mt-6 max-w-5xl px-5 md:px-8">
          <div data-testid="ad-slot" className="border-2 border-dashed border-neutral-300 bg-white px-4 py-3 text-center text-xs font-bold uppercase tracking-widest text-neutral-400">
            Ad slot — this seller is on the free plan
          </div>
        </div>
      )}

      {/* Products */}
      <main className="mx-auto max-w-5xl px-5 py-10 md:px-8 md:py-14">
        {(() => {
          const products = Array.isArray(shop?.products) ? shop.products : [];
          return (
            <>
              <div className="mb-8 flex items-baseline justify-between">
                <h2 className="mk-head text-xl font-extrabold uppercase tracking-widest">Products</h2>
                <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{products.length} items</span>
              </div>

              {products.length === 0 ? (
                <div className="border-2 border-[#0A0A0A] bg-white p-12 text-center" data-testid="shop-empty">
                  <Package className="mx-auto h-8 w-8 text-neutral-300" />
                  <p className="mt-3 text-sm text-[#525252]">This shop hasn't listed any products yet.</p>
                </div>
              ) : (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {products.map((p) => {
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
                        <div className="flex flex-1 flex-col p-5">
                          <div className="flex items-start justify-between gap-3">
                            <h3 className="text-base font-bold leading-snug">{p.title}</h3>
                            <span className="mk-head shrink-0 text-lg font-black tracking-tighter">₹{unitPrice(p)}</span>
                          </div>
                          {p.description && <p className="mt-2 text-sm leading-relaxed text-[#525252]">{p.description}</p>}
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
                                  className="mt-1 w-full border-2 border-[#0A0A0A] bg-white px-2.5 py-2 text-sm outline-none focus:border-[#FF4F00]"
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
                            className="mt-5 inline-flex items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
                          >
                            {sold ? "Sold out" : <>Add to cart <ShoppingBag className="h-4 w-4" /></>}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          );
        })()}

        {/* Cart */}
        <div id="cart" className="mt-14 scroll-mt-20 border-2 border-[#0A0A0A] bg-white shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]">
          <div className="flex items-center justify-between border-b-2 border-[#0A0A0A] bg-[#FAFAFA] px-5 py-3">
            <h2 className="mk-head text-base font-extrabold uppercase tracking-widest">Your cart</h2>
            <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{cart.length} items</span>
          </div>
          <div className="p-5 sm:p-6">
            {cart.length === 0 ? (
              <p className="text-sm text-[#525252]" data-testid="cart-empty">Your cart is empty. Add something you love.</p>
            ) : (
              <>
                <ul data-testid="cart-list" className="divide-y divide-[#E5E5E5]">
                  {cart.map((c, i) => (
                    <li key={i} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <span className="font-medium">{c.title}</span>
                        {Object.keys(c.optionSelections).length > 0 && <span className="ml-2 text-sm text-[#525252]">{Object.values(c.optionSelections).join(", ")}</span>}
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="font-bold">₹{c.unitPrice}</span>
                        <button data-testid={`cart-remove-${i}`} onClick={() => removeItem(i)} aria-label="Remove item" className="text-[#8A2200] transition-colors hover:text-[#FF4F00]"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </li>
                  ))}
                </ul>
                <div className="mt-4 flex items-center justify-between border-t-2 border-[#0A0A0A] pt-4">
                  <span className="text-sm font-bold uppercase tracking-widest text-[#525252]">Total</span>
                  <span className="mk-head text-2xl font-black tracking-tighter" data-testid="cart-total">₹{cartTotal}</span>
                </div>
                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Your name</span>
                    <input data-testid="buyer-name" value={buyer.buyerName || ""} onChange={(e) => setBuyer({ ...buyer, buyerName: e.target.value })} placeholder="Full name" className="mt-1.5 w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#FF4F00]" />
                  </label>
                  <label className="block">
                    <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Your email</span>
                    <input data-testid="buyer-email" value={buyer.buyerEmail || ""} onChange={(e) => setBuyer({ ...buyer, buyerEmail: e.target.value })} placeholder="you@example.com" className="mt-1.5 w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none focus:border-[#FF4F00]" />
                  </label>
                </div>
                <div className="mt-6">
                  <Btn variant="primary" data-testid="checkout-btn" onClick={checkout} disabled={placing || !buyer.buyerName || !buyer.buyerEmail}>
                    {placing ? "Placing…" : <>Place order <ArrowRight className="h-4 w-4" /></>}
                  </Btn>
                </div>
              </>
            )}
            {err && <p className="mt-4 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-4 py-2.5 text-sm font-medium text-[#8A2200]" data-testid="checkout-error">{err}</p>}
          </div>
        </div>
      </main>
    </div>
  );
}

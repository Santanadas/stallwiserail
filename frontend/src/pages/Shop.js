import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { ShoppingBag, Store, ArrowRight, Package, Share2, Check } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import CartDrawer from "@/components/CartDrawer";
import { useCart, unitPriceFor, isSoldOut } from "@/lib/useCart";
import { useCheckout } from "@/lib/useCheckout";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

function initials(name) {
  return (name || "S").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export default function Shop() {
  const { storeSlug } = useParams();
  const [shop, setShop] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [selections, setSelections] = useState({});
  const [buyer, setBuyer] = useState({ buyerName: "", buyerEmail: "", buyerPhone: "" });
  const [copied, setCopied] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [payMethod, setPayMethod] = useState("online");

  const { cart, addItem, removeItem, setQty, clear, cartTotal, cartCount, allowedPayments } =
    useCart(storeSlug);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/shop/${storeSlug}`);
      setShop(data);
    } catch (e) { setLoadErr(formatApiError(e.response?.data?.detail)); }
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

  const unitPrice = (p) => unitPriceFor(p, selections[p.product_id] || {});

  const productsList = Array.isArray(shop?.products) ? shop.products : [];

  const { checkout, placing, err, setErr } = useCheckout({
    storeSlug,
    storeName: shop?.store?.name,
    cart,
    cartTotal,
    payMethod,
    clear,
  });

  useEffect(() => {
    if (allowedPayments.length && !allowedPayments.includes(payMethod)) {
      setPayMethod(allowedPayments[0]);
    }
  }, [allowedPayments, payMethod]);

  const addToCart = (p) => {
    const sel = selections[p.product_id] || {};
    for (const g of p.optionGroups || []) {
      if (!g?.name) continue;
      if (!sel[g.name]) { setErr(`Pick a ${g.name} for ${p.title}`); return; }
      const opt = (g.options || []).find((o) => o?.label === sel[g.name]);
      if (opt && opt.stock === 0) { setErr(`${g.name} ${opt.label} is out of stock`); return; }
    }
    setErr("");
    addItem({
      productId: p.product_id,
      title: p.title,
      quantity: 1,
      optionSelections: sel,
      unitPrice: unitPrice(p),
      paymentMethods: (p.paymentMethods && p.paymentMethods.length) ? p.paymentMethods : ["online"],
    });
    setCartOpen(true);
  };

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

  // Keep these in step with backend/seo.py store_meta() so the tags don't flip
  // between the server-rendered document and the client render.
  useDocumentMeta({
    title: shop?.store?.name ? `${shop.store.name} — Shop Online | Stall Wise` : "Shop | Stall Wise",
    description:
      shop?.store?.bio ||
      `Shop ${productsList.length || ""} products from ${shop?.store?.name || "this seller"} on Stall Wise. Pay securely by UPI, card or cash on delivery — your money goes straight to the seller.`,
    path: `/${storeSlug}`,
    schemaData: shopSchema,
    image: shop?.seller?.avatar ? fileUrl(shop.seller.avatar) : undefined,
  });

  if (loadErr && !shop) return (
    <div className="mk flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FAFAFA] px-6 text-center" data-testid="shop-error">
      <Store className="h-10 w-10 text-neutral-300" />
      <p className="mk-head text-2xl font-black tracking-tighter">Shop not found</p>
      <p className="max-w-sm text-sm text-[#525252]">{loadErr}</p>
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
              {cartCount > 0 && <span className="ml-1 border border-[#0A0A0A] bg-[#FF4F00] px-1.5 text-xs text-white" data-testid="cart-count">{cartCount}</span>}
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
                  <Link
                    to={p.slug ? `/${storeSlug}/${p.slug}` : `/${storeSlug}`}
                    aria-label={p.title}
                    className="relative block aspect-square overflow-hidden border-b-2 border-[#0A0A0A] bg-[#FAFAFA]"
                  >
                    {p.image ? (
                      <img src={fileUrl(p.image)} alt={p.title} className="h-full w-full object-cover" loading="lazy" />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center"><Package className="h-10 w-10 text-neutral-300" /></div>
                    )}
                    {sold && <div className="absolute inset-0 flex items-center justify-center bg-white/70"><span className="border-2 border-[#0A0A0A] bg-white px-3 py-1 text-xs font-black uppercase tracking-widest">Sold out</span></div>}
                  </Link>
                  <div className="flex flex-1 flex-col p-4 sm:p-5">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-base font-bold leading-snug">
                        <Link
                          to={p.slug ? `/${storeSlug}/${p.slug}` : `/${storeSlug}`}
                          data-testid={`product-link-${p.product_id}`}
                          className="hover:text-[#FF4F00]"
                        >
                          {p.title}
                        </Link>
                      </h3>
                      <span className="mk-head shrink-0 text-lg font-black tracking-tighter">₹{unitPrice(p)}</span>
                    </div>
                    {p.description && <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-[#525252]">{p.description}</p>}
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
              <span className="text-xs text-neutral-400">{cartCount} {cartCount === 1 ? "item" : "items"}</span>
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
        deliveryFee={shop?.store?.deliveryFee || 0}
        freeDeliveryAbove={shop?.store?.freeDeliveryAbove ?? null}
        buyer={buyer}
        setBuyer={setBuyer}
        checkout={() => checkout(buyer)}
        placing={placing}
        err={err}
        allowedPayments={allowedPayments}
        payMethod={payMethod}
        setPayMethod={setPayMethod}
      />
    </div>
  );
}

import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ShoppingBag, Store, ArrowRight, Package, Share2, Check, ShieldCheck,
  Truck, Clock, Banknote, CreditCard, User,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import CartDrawer from "@/components/CartDrawer";
import { useCart, isSoldOut } from "@/lib/useCart";
import { useCheckout } from "@/lib/useCheckout";
import { useDocumentMeta } from "@/lib/useDocumentMeta";
import { CATEGORIES, percentOff } from "@/lib/productMeta";

function initials(name) {
  return (name || "S").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

const rupees = (n) => `₹${Math.round(Number(n) || 0).toLocaleString("en-IN")}`;

const acceptsCod = (p) => (p.paymentMethods || []).includes("cod");
const acceptsOnlineMethod = (p) => (p.paymentMethods || ["online"]).includes("online");

/**
 * The cheapest a buyer can get this product for, and whether that is the only
 * price. A tile has room for one number; when options change the price it has
 * to say "from", or the buyer is quoted a figure they cannot actually pay.
 */
function tilePrice(p) {
  let price = Number(p.price || 0);
  let varies = false;
  for (const g of p.optionGroups || []) {
    const opts = (g?.options || []).filter((o) => o && o.label && o.stock !== 0);
    if (!opts.length) continue;
    const deltas = opts.map((o) => Number(o.priceDelta || 0));
    const low = Math.min(...deltas);
    if (Math.max(...deltas) !== low) varies = true;
    price += low;
  }
  return { price, varies };
}

/**
 * Why a stranger's link is safe to buy from. Every line is a setting the shop
 * endpoint already returns, or a mechanic every order goes through — nothing
 * here is decoration, and a line whose fact is missing is left out rather than
 * filled in.
 */
function trustPoints(shop, products) {
  const s = shop.store || {};
  const points = [];

  const fee = Number(s.deliveryFee || 0);
  const threshold = s.freeDeliveryAbove;
  if (fee <= 0) {
    points.push({ icon: Truck, title: "Free delivery", sub: "on every order", long: "Free delivery on every order" });
  } else if (threshold != null) {
    points.push({ icon: Truck, title: "Free delivery", sub: `over ${rupees(threshold)}`, long: `Free delivery over ${rupees(threshold)}` });
  } else {
    points.push({ icon: Truck, title: `Delivery ${rupees(fee)}`, sub: "flat, any order", long: `Flat ${rupees(fee)} delivery` });
  }

  const days = s.dispatchDays ?? 2;
  const ships = days <= 0 ? "Ships today" : `Ships in ${days} day${days === 1 ? "" : "s"}`;
  points.push({ icon: Clock, title: ships, sub: "after you order", long: days <= 0 ? "Dispatched the day you order" : `Dispatched in ${days} day${days === 1 ? "" : "s"}` });

  const cod = products.some(acceptsCod);
  const online = shop.acceptsOnline !== false && products.some(acceptsOnlineMethod);
  if (cod && online) {
    points.push({ icon: Banknote, title: "Cash on delivery", sub: "or UPI & cards", long: "UPI, cards or cash on delivery" });
  } else if (online) {
    points.push({ icon: CreditCard, title: "UPI & cards", sub: "netbanking too", long: "UPI, cards and netbanking" });
  } else if (cod) {
    points.push({ icon: Banknote, title: "Cash on delivery", sub: "pay at your door", long: "Cash on delivery — pay at your door" });
  }

  points.push({
    icon: ShieldCheck,
    title: "You confirm it",
    sub: "code at handover",
    long: "Delivery is yours to confirm",
    detail: "You get a code by email and give it to the seller at handover.",
    highlight: true,
  });
  return points;
}

export default function Shop() {
  const { storeSlug } = useParams();
  const [shop, setShop] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [buyer, setBuyer] = useState({ buyerName: "", buyerEmail: "", buyerPhone: "" });
  const [copied, setCopied] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [payMethod, setPayMethod] = useState("online");
  const [category, setCategory] = useState("all");

  // Items are added on each product's own page; the cart lives in
  // localStorage per shop, so it is already here when the buyer comes back.
  const { cart, removeItem, setQty, clear, cartTotal, cartCount, allowedPayments } =
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

  const productsList = Array.isArray(shop?.products) ? shop.products : [];
  // Category chips only earn their space once a shop spans two or more.
  const shopCategories = CATEGORIES.filter((c) => productsList.some((p) => p.category === c.id));
  const activeCategory = shopCategories.some((c) => c.id === category) ? category : "all";
  const visibleProducts =
    activeCategory === "all" ? productsList : productsList.filter((p) => p.category === activeCategory);

  const { checkout, placing, err, setErr } = useCheckout({
    storeSlug,
    storeName: shop?.store?.name,
    cart,
    cartTotal,
    payMethod,
    clear,
  });

  // The shop can only be offered online payment if the seller can actually be
  // paid: checkout refuses otherwise, and finding that out after typing in a
  // delivery address is worse than never seeing the option.
  const payable = allowedPayments.filter(
    (m) => m !== "online" || shop?.acceptsOnline !== false
  );

  useEffect(() => {
    if (payable.length && !payable.includes(payMethod)) {
      setPayMethod(payable[0]);
    }
  }, [payable, payMethod]);

  // Mirrors delivery_for() on the server, same as the cart drawer: the bar
  // says "Checkout ₹X", so X has to be what the buyer will actually be asked
  // for, delivery included.
  const fee = Number(shop?.store?.deliveryFee || 0);
  const threshold = shop?.store?.freeDeliveryAbove ?? null;
  const delivery = fee > 0 && !(threshold != null && cartTotal >= threshold) ? fee : 0;

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

  const points = trustPoints(shop, productsList);
  const codOnly = shop.acceptsOnline === false && productsList.some(acceptsCod);
  const shopName = shop.store?.name || "Shop";

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

      {/* Who this is, and what they promise. On a wide screen both sit in one
          band so a buyer takes them in at a glance without the terms pushing
          the products below the fold. */}
      <section className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-6 sm:px-6 sm:py-10 md:px-8 lg:flex-row lg:items-start lg:gap-10 lg:py-10">
          <div className="min-w-0 flex-1">
            <div className="flex items-start gap-4 sm:gap-5">
              <div className="flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00] shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] sm:h-24 sm:w-24 sm:shadow-[5px_5px_0px_0px_rgba(10,10,10,1)]" data-testid="shop-avatar">
                {shop.seller?.avatar ? (
                  <img src={fileUrl(shop.seller.avatar)} alt={shopName} className="h-full w-full object-cover" />
                ) : (
                  <span className="mk-head text-[26px] font-black text-white sm:text-3xl">{initials(shop.store?.name)}</span>
                )}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-x-3.5 gap-y-2">
                  <h1 data-testid="shop-name" className="mk-head text-[32px] font-black leading-[1.05] tracking-tighter sm:text-5xl">{shopName}</h1>
                  {/* Earned at 50 completed orders, never bought — see
                      VERIFIED_AFTER_ORDERS in server.py. The words sit next to
                      the mark because an unexplained tick reassures nobody. */}
                  {shop.verified && (
                    <span
                      data-testid="verified-badge"
                      title="This seller has completed 50 or more orders without a dispute."
                      className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-2 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-white sm:px-2.5 sm:text-[11px]"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 text-[#FF4F00]" strokeWidth={2.5} />
                      Verified seller
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-xs font-medium text-[#525252] sm:text-sm">
                  stallwise.in/<span className="font-bold text-[#0A0A0A]">{shop.store?.slug || storeSlug}</span>
                </p>
              </div>
            </div>
            {shop.store?.bio && (
              <p className="mt-4 max-w-xl text-sm leading-relaxed text-[#525252] [text-wrap:pretty] sm:text-[15px]" data-testid="shop-bio">{shop.store.bio}</p>
            )}
            {shop.seller?.name && (
              <div className="mt-4 flex items-center gap-2 border-t border-[#E5E5E5] pt-4 lg:border-t-0 lg:pt-0">
                <User className="h-4 w-4 text-[#525252]" />
                <span className="text-xs font-semibold text-[#525252] sm:text-[13px]">
                  Sold by <span className="font-bold text-[#0A0A0A]">{shop.seller.name}</span>
                </span>
              </div>
            )}
          </div>

          {/* Desktop: the promises as one card beside the identity. */}
          <div className="hidden w-[300px] shrink-0 border-2 border-[#0A0A0A] bg-white shadow-[5px_5px_0px_0px_rgba(10,10,10,1)] lg:block" data-testid="shop-trust">
            {points.map((pt, i) => (
              <div
                key={pt.long}
                className={`flex items-start gap-3 px-4 py-3 ${i < points.length - 1 ? "border-b-2 border-[#0A0A0A]" : ""} ${pt.highlight ? "bg-[#FFF4E0]" : ""}`}
              >
                <pt.icon className="mt-0.5 h-[19px] w-[19px] shrink-0" />
                <div>
                  <div className="text-[13px] font-bold leading-snug">{pt.long}</div>
                  {pt.detail && <div className="mt-1 text-xs leading-snug text-[#525252]">{pt.detail}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Phone: the same promises as a 2-up grid of cells. The black shows
            through the 2px gaps as shared rules; an odd last cell spans both
            columns so no gap is left as a black hole. */}
        <div className="grid grid-cols-2 gap-[2px] border-t-2 border-[#0A0A0A] bg-[#0A0A0A] lg:hidden">
          {points.map((pt, i) => (
            <div
              key={pt.long}
              className={`flex items-center gap-2.5 px-4 py-3.5 ${pt.highlight ? "bg-[#FFF4E0]" : "bg-white"} ${points.length % 2 === 1 && i === points.length - 1 ? "col-span-2" : ""}`}
            >
              <pt.icon className="h-5 w-5 shrink-0" />
              <div className="min-w-0">
                <div className="text-xs font-extrabold leading-tight">{pt.title}</div>
                <div className="text-[11px] font-medium text-[#525252]">{pt.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10 md:px-8">
        {codOnly && (
          // Today this is every shop whose payouts are not live yet. Saying so
          // up front beats a buyer finding out after typing in an address.
          <div className="mb-6 flex items-start gap-3 border-2 border-[#0A0A0A] bg-[#FFF4E0] p-4 shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]" data-testid="cod-only">
            <Banknote className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="text-sm font-extrabold">This shop takes cash on delivery</p>
              <p className="mt-1 text-[13px] leading-relaxed text-[#525252]">Pay the seller when your order arrives. Card and UPI aren't switched on here yet.</p>
            </div>
          </div>
        )}

        <div className="mb-3.5 flex items-baseline justify-between sm:mb-5">
          <h2 className="mk-head text-[17px] font-extrabold uppercase tracking-[0.14em] sm:text-xl">Products</h2>
          <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#525252] sm:text-xs">
            {visibleProducts.length} {visibleProducts.length === 1 ? "item" : "items"}
          </span>
        </div>

        {shopCategories.length > 1 && (
          <div
            data-testid="shop-categories"
            className="-mx-4 mb-3.5 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:mb-5 sm:flex-wrap sm:px-0"
          >
            {[{ id: "all", label: "All" }, ...shopCategories].map((c) => {
              const on = activeCategory === c.id;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setCategory(c.id)}
                  aria-pressed={on}
                  className={`shrink-0 border-2 border-[#0A0A0A] px-3 py-1.5 text-xs font-extrabold uppercase tracking-[0.08em] transition-colors ${on ? "bg-[#0A0A0A] text-white" : "bg-white hover:bg-[#FFF4E0]"}`}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        )}

        {productsList.length === 0 ? (
          <div className="border-2 border-[#0A0A0A] bg-white px-6 py-10 text-center shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] sm:py-12" data-testid="shop-empty">
            <Package className="mx-auto h-8 w-8 text-neutral-300" strokeWidth={1.75} />
            <p className="mt-3 text-[15px] font-extrabold">{shop.seller?.name || shopName} hasn't listed anything yet</p>
            <p className="mt-1 text-[13px] text-[#525252]">Save the link — this shop is just getting started.</p>
          </div>
        ) : (
          /* A dense square grid, the way a shop reads on Instagram: the photo
             is the product. The 2px rules are the grid gap showing through a
             black container, so every hairline is shared. Names live on the
             product page — on a grid this tight a caption fights the thing it
             captions — but price stays, because nobody should have to tap to
             learn it. */
          <div className="grid grid-cols-2 gap-[2px] border-2 border-[#0A0A0A] bg-[#0A0A0A] lg:grid-cols-3">
            {visibleProducts.map((p) => {
              const sold = isSoldOut(p);
              const { price, varies } = tilePrice(p);
              const priceLabel = `${varies ? "From " : ""}${rupees(price)}`;
              // Same rule as the product page: option deltas move MRP too.
              const off = percentOff(price, p.mrp ? p.mrp + (price - p.price) : 0);
              return (
                <Link
                  key={p.product_id}
                  to={p.slug ? `/${storeSlug}/${p.slug}` : `/${storeSlug}`}
                  data-testid={`shop-product-${p.product_id}`}
                  aria-label={`${p.title}, ${priceLabel}${sold ? ", sold out" : ""}`}
                  className="group relative block aspect-square overflow-hidden bg-white outline-none focus-visible:z-10 focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[#FF4F00]"
                >
                  {p.image ? (
                    <img
                      src={fileUrl(p.image)}
                      alt=""
                      loading="lazy"
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.04]"
                    />
                  ) : (
                    // A seller who hasn't uploaded a photo should still look
                    // like a shop, not a hole in the grid.
                    <div className="flex h-full w-full items-center justify-center bg-[repeating-linear-gradient(135deg,#FAFAFA,#FAFAFA_9px,#F0F0F0_9px,#F0F0F0_18px)]">
                      <Package className="h-8 w-8 text-[#C4C4C4] sm:h-10 sm:w-10" strokeWidth={1.75} />
                    </div>
                  )}

                  {acceptsCod(p) && !sold && (
                    <span className="absolute left-2 top-2 border-[1.5px] border-[#0A0A0A] bg-[#FFF4E0] px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-[0.08em] sm:left-3 sm:top-3 sm:px-2 sm:text-[10px]">
                      <span className="sm:hidden">COD</span>
                      <span className="hidden sm:inline">Cash on delivery</span>
                    </span>
                  )}

                  {off > 0 && !sold && (
                    <span className="absolute right-2 top-2 border-[1.5px] border-[#0A0A0A] bg-[#FF4F00] px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-[0.08em] text-white sm:right-3 sm:top-3 sm:px-2 sm:text-[10px]">
                      {off}% off
                    </span>
                  )}

                  {sold ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                      <span className="border-2 border-[#0A0A0A] bg-white px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] sm:px-3.5 sm:py-1.5 sm:text-xs">Sold out</span>
                    </div>
                  ) : (
                    <span className="mk-head absolute bottom-2 left-2 border-[1.5px] border-[#0A0A0A] bg-white px-2 py-0.5 text-sm font-black tracking-tight transition-colors group-hover:bg-[#0A0A0A] group-hover:text-white sm:bottom-3 sm:left-3 sm:border-2 sm:px-2.5 sm:py-1 sm:text-lg">
                      {priceLabel}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        )}

        {shop.showAds && (
          <div data-testid="ad-slot" className="mt-5 border-2 border-dashed border-neutral-300 bg-white px-4 py-3.5 text-center text-[10px] font-extrabold uppercase tracking-[0.16em] text-neutral-400 sm:mt-7">
            Advertisement
          </div>
        )}
      </main>

      {/* Sticky mobile cart bar */}
      {cart.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-3 text-white shadow-2xl sm:hidden">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <span className="text-[11px] font-semibold text-neutral-400">
                {cartCount} {cartCount === 1 ? "item" : "items"} · {delivery > 0 ? `+ ${rupees(delivery)} delivery` : "delivery free"}
              </span>
              <p className="mk-head text-xl font-black tracking-tight text-white">{rupees(cartTotal + delivery)}</p>
            </div>
            <button
              type="button"
              onClick={() => setCartOpen(true)}
              className="inline-flex min-h-[44px] items-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-4 py-2 text-xs font-black uppercase tracking-wider text-white"
            >
              Checkout <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.5} />
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
        allowedPayments={payable}
        payMethod={payMethod}
        setPayMethod={setPayMethod}
      />
    </div>
  );
}

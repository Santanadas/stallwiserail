import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ShoppingBag, Package, ChevronRight, Store, ArrowLeft, Check } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import CartDrawer from "@/components/CartDrawer";
import { useCart, unitPriceFor, isSoldOut } from "@/lib/useCart";
import { useCheckout } from "@/lib/useCheckout";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function ProductPage() {
  const { storeSlug, productSlug } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [selections, setSelections] = useState({});
  const [activeImg, setActiveImg] = useState(0);
  const [cartOpen, setCartOpen] = useState(false);
  const [added, setAdded] = useState(false);
  const [buyer, setBuyer] = useState({ buyerName: "", buyerEmail: "", buyerPhone: "" });
  const [payMethod, setPayMethod] = useState("online");

  const { cart, addItem, removeItem, setQty, clear, cartTotal, cartCount, allowedPayments } =
    useCart(storeSlug);

  const load = useCallback(async () => {
    try {
      const { data: d } = await api.get(`/shop/${storeSlug}/product/${productSlug}`);
      setData(d);
      setActiveImg(0);
    } catch (e) {
      setLoadErr(formatApiError(e.response?.data?.detail));
    }
  }, [storeSlug, productSlug]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (allowedPayments.length && !allowedPayments.includes(payMethod)) setPayMethod(allowedPayments[0]);
  }, [allowedPayments, payMethod]);

  const product = data?.product;
  const store = data?.store;
  const price = product ? unitPriceFor(product, selections) : 0;
  const sold = product ? isSoldOut(product) : false;
  const images = product?.images?.length ? product.images : product?.image ? [product.image] : [];

  const { checkout, placing, err, setErr } = useCheckout({
    storeSlug,
    storeName: store?.name,
    cart,
    cartTotal,
    payMethod,
    clear,
  });

  // Mirrors backend/seo.py product_meta() so the server-rendered tags and the
  // client-rendered ones agree.
  useDocumentMeta({
    title: product ? `${product.title} — ₹${Math.round(price).toLocaleString("en-IN")} | ${store?.name}` : "Product | Stall Wise",
    description:
      product?.description ||
      (product
        ? `Buy ${product.title} from ${store?.name} on Stall Wise. Pay by ${
            (product.paymentMethods || []).includes("cod") ? "cash on delivery" : "UPI, card or netbanking"
          } — your money goes straight to the seller.`
        : ""),
    path: `/${storeSlug}/${productSlug}`,
    image: images[0] ? fileUrl(images[0]) : undefined,
  });

  const addToCart = () => {
    if (!product) return;
    for (const g of product.optionGroups || []) {
      if (!g?.name) continue;
      if (!selections[g.name]) { setErr(`Pick a ${g.name}`); return; }
      const opt = (g.options || []).find((o) => o?.label === selections[g.name]);
      if (opt && opt.stock === 0) { setErr(`${g.name} ${opt.label} is out of stock`); return; }
    }
    setErr("");
    addItem({
      productId: product.product_id,
      title: product.title,
      quantity: 1,
      optionSelections: selections,
      unitPrice: price,
      paymentMethods: product.paymentMethods || ["online"],
    });
    setAdded(true);
    setTimeout(() => setAdded(false), 1600);
  };

  if (loadErr && !data) {
    return (
      <div className="mk flex min-h-screen flex-col items-center justify-center gap-4 bg-[#FAFAFA] px-6 text-center">
        <Package className="h-10 w-10 text-neutral-300" />
        <p className="mk-head text-2xl font-black tracking-tighter">Product not found</p>
        <p className="max-w-sm text-sm text-[#525252]">{loadErr}</p>
        <Link to={`/${storeSlug}`} className="mt-2 border-2 border-[#0A0A0A] bg-white px-5 py-2.5 text-sm font-bold transition-transform hover:-translate-y-0.5">
          Back to the shop
        </Link>
      </div>
    );
  }
  if (!data) return <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA] text-sm text-[#525252]">Loading…</div>;

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] pb-24 text-[#0A0A0A] sm:pb-12">
      <header className="sticky top-0 z-50 border-b-2 border-[#0A0A0A] bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6 md:px-8">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter sm:text-xl">
            STALL WISE<span className="text-[#FF4F00]">.</span>
          </Link>
          <button
            type="button"
            onClick={() => setCartOpen(true)}
            className="relative inline-flex min-h-[40px] items-center gap-2 border-2 border-[#0A0A0A] bg-white px-3 py-1.5 text-xs font-bold transition-transform hover:-translate-y-0.5 sm:text-sm"
            data-testid="cart-jump"
          >
            <ShoppingBag className="h-4 w-4" /> Cart
            {cartCount > 0 && (
              <span className="ml-1 border border-[#0A0A0A] bg-[#FF4F00] px-1.5 text-xs text-white">{cartCount}</span>
            )}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 md:px-8 md:py-10">
        {/* Breadcrumbs — real internal links for crawlers and humans */}
        <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-[#525252]">
          <Link to="/shops" className="hover:text-[#FF4F00]">Shops</Link>
          <ChevronRight className="h-3 w-3" />
          <Link to={`/${storeSlug}`} className="font-bold text-[#0A0A0A] hover:text-[#FF4F00]">{store?.name}</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="truncate">{product.title}</span>
        </nav>

        <div className="grid gap-8 md:grid-cols-2">
          {/* Gallery */}
          <div>
            <div className="aspect-square overflow-hidden border-2 border-[#0A0A0A] bg-white">
              {images[activeImg] ? (
                <img src={fileUrl(images[activeImg])} alt={product.title} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center"><Package className="h-12 w-12 text-neutral-300" /></div>
              )}
            </div>
            {images.length > 1 && (
              <div className="mt-3 flex gap-2 overflow-x-auto">
                {images.map((src, i) => (
                  <button
                    key={src + i}
                    type="button"
                    onClick={() => setActiveImg(i)}
                    aria-label={`View image ${i + 1}`}
                    className={`h-16 w-16 shrink-0 overflow-hidden border-2 ${i === activeImg ? "border-[#FF4F00]" : "border-[#0A0A0A]"}`}
                  >
                    <img src={fileUrl(src)} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Detail */}
          <div>
            <h1 className="mk-head text-3xl font-black leading-tight tracking-tighter sm:text-4xl">{product.title}</h1>
            <p className="mk-head mt-3 text-3xl font-black tracking-tighter text-[#0A0A0A]">
              ₹{price.toLocaleString("en-IN")}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              {product.stock != null && (
                <span className={`border border-[#0A0A0A] px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${product.stock === 0 ? "bg-[#FFE9E0] text-[#8A2200]" : "bg-[#E6F6EC] text-[#0B5227]"}`}>
                  {product.stock === 0 ? "Out of stock" : `${product.stock} in stock`}
                </span>
              )}
              {(product.paymentMethods || []).includes("cod") && (
                <span className="border border-[#0A0A0A] bg-[#FFF4E0] px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider">
                  Cash on delivery
                </span>
              )}
            </div>

            {product.description && (
              <p className="mt-5 whitespace-pre-line text-sm leading-relaxed text-[#525252]">{product.description}</p>
            )}

            {/* Variants */}
            <div className="mt-6 space-y-4">
              {(product.optionGroups || []).filter((g) => g && g.name).map((g) => (
                <div key={g.name}>
                  <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{g.name}</span>
                  <select
                    data-testid={`option-${g.name}`}
                    value={selections[g.name] || ""}
                    onChange={(e) => setSelections({ ...selections, [g.name]: e.target.value })}
                    className="mt-1.5 w-full min-h-[44px] border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-base outline-none focus:border-[#FF4F00] sm:text-sm"
                  >
                    <option value="">Select</option>
                    {(g.options || []).filter((o) => o && o.label).map((o) => (
                      <option key={o.label} value={o.label} disabled={o.stock === 0}>
                        {o.label}{o.priceDelta ? ` (+₹${o.priceDelta})` : ""}{o.stock === 0 ? " — sold out" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <button
              data-testid="add-cart-btn"
              onClick={addToCart}
              disabled={sold}
              className="mt-6 inline-flex w-full min-h-[52px] items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-5 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
            >
              {sold ? "Sold out" : added ? <><Check className="h-4 w-4" /> Added to cart</> : <>Add to cart <ShoppingBag className="h-4 w-4" /></>}
            </button>

            {err && (
              <p className="mt-4 border-2 border-[#0A0A0A] bg-[#FFE9E0] px-4 py-2.5 text-sm font-medium text-[#8A2200]">{err}</p>
            )}

            {/* Seller */}
            <Link
              to={`/${storeSlug}`}
              className="mt-6 flex items-center gap-3 border-2 border-[#0A0A0A] bg-white p-4 transition-transform hover:-translate-y-0.5"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00]">
                {data.seller?.avatar
                  ? <img src={fileUrl(data.seller.avatar)} alt="" className="h-full w-full object-cover" />
                  : <Store className="h-5 w-5 text-white" />}
              </div>
              <div className="min-w-0">
                <span className="text-[11px] font-bold uppercase tracking-widest text-[#525252]">Sold by</span>
                <p className="truncate font-bold">{store?.name}</p>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 shrink-0 text-[#525252]" />
            </Link>
          </div>
        </div>

        {/* Related — internal links so crawlers reach every product */}
        {data.related?.length > 0 && (
          <section className="mt-14">
            <h2 className="mk-head text-lg font-extrabold uppercase tracking-widest">More from {store?.name}</h2>
            <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {data.related.map((p) => (
                <Link
                  key={p.product_id}
                  to={`/${storeSlug}/${p.slug}`}
                  className="group border-2 border-[#0A0A0A] bg-white transition-transform hover:-translate-y-1 hover:shadow-[5px_5px_0px_0px_rgba(10,10,10,1)]"
                >
                  <div className="aspect-square overflow-hidden border-b-2 border-[#0A0A0A] bg-[#FAFAFA]">
                    {p.image
                      ? <img src={fileUrl(p.image)} alt={p.title} loading="lazy" className="h-full w-full object-cover" />
                      : <div className="flex h-full w-full items-center justify-center"><Package className="h-8 w-8 text-neutral-300" /></div>}
                  </div>
                  <div className="p-3">
                    <p className="line-clamp-1 text-sm font-bold">{p.title}</p>
                    <p className="mk-head mt-1 font-black tracking-tighter">₹{p.price}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        <Link to={`/${storeSlug}`} className="mt-10 inline-flex items-center gap-2 text-sm font-bold hover:text-[#FF4F00]">
          <ArrowLeft className="h-4 w-4" /> All products from {store?.name}
        </Link>
      </main>

      {cart.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t-2 border-[#0A0A0A] bg-[#0A0A0A] p-3 text-white sm:hidden">
          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-xs text-neutral-400">{cartCount} {cartCount === 1 ? "item" : "items"}</span>
              <p className="mk-head text-lg font-black text-white">₹{cartTotal}</p>
            </div>
            <button
              type="button"
              onClick={() => setCartOpen(true)}
              className="inline-flex min-h-[42px] items-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-4 py-2 text-xs font-black uppercase tracking-wider text-white"
            >
              Checkout
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

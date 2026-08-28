import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, BadgeIndianRupee, Link2, Zap, Store, PackagePlus, Share2, Check } from "lucide-react";
import SiteFooter from "@/components/SiteFooter";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const STEPS = [
  {
    n: "01",
    title: "Create your shop",
    desc: "Sign up, pick your handle, and your shop is live at marketo.com/your-name.",
    icon: Store,
    img: "https://images.unsplash.com/photo-1740710543611-80b658171bc3?crop=entropy&cs=srgb&fm=jpg&w=800&q=70&ixlib=rb-4.1.0",
    alt: "Maker working in a studio",
  },
  {
    n: "02",
    title: "List products",
    desc: "Add photos, prices and options like size or colour. Stock counts update themselves.",
    icon: PackagePlus,
    img: "https://images.unsplash.com/photo-1449247666642-264389f5f5b1?crop=entropy&cs=srgb&fm=jpg&w=800&q=70&ixlib=rb-4.1.0",
    alt: "Seller packing a customer order",
  },
  {
    n: "03",
    title: "Share your link, get paid",
    desc: "Drop the link in your bio. Payments land in your own Razorpay account, not ours.",
    icon: Share2,
    img: "https://images.unsplash.com/photo-1509017174183-0b7e0278f1ec?crop=entropy&cs=srgb&fm=jpg&w=800&q=70&ixlib=rb-4.1.0",
    alt: "Customer paying on a mobile phone",
  },
];

const REASONS = [
  { k: "0%", title: "Commission", desc: "We never take a cut of a sale. Not on your first order, not on your thousandth.", icon: BadgeIndianRupee },
  { k: "Direct", title: "Payments", desc: "Buyers pay your Razorpay account. No escrow, no 7-day hold, no payout requests.", icon: Zap },
  { k: "Free", title: "To start", desc: "No setup fee, no card needed. Open a shop and start listing today.", icon: Check },
  { k: "Yours", title: "Own link", desc: "One clean URL you can put in a bio, a story or a WhatsApp message.", icon: Link2 },
];

const PLANS = [
  { name: "Free", price: "₹0", period: "forever", note: "Shows Marketo ads on your shop", feats: ["Unlimited products", "0% commission", "Delivery OTP + dispute protection"], dark: false, badge: null },
  { name: "Pro Monthly", price: "₹149", period: "per month", note: "Ad-free shop page", feats: ["Everything in Free", "No ads on your shop", "Cancel anytime"], dark: false, badge: null },
  { name: "Pro Yearly", price: "₹999", period: "per year", note: "Ad-free, best value", feats: ["Everything in Pro Monthly", "Save ₹789 a year", "Priority support"], dark: true, badge: "Best value" },
];

export default function Landing() {
  const [slug, setSlug] = useState("");
  const navigate = useNavigate();
  useDocumentMeta({
    title: "Marketo | Zero-Commission Marketplace — Open Your Own Shop",
    description:
      "Open your own shop at marketo.com/your-name, list products and get paid directly into your Razorpay account. 0% commission, free to start.",
    path: "/",
  });

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="landing-page">
      <header className="sticky top-0 z-50 border-b border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-10">
          <a href="/" className="mk-head text-xl font-black tracking-tighter" data-testid="brand-logo" aria-label="Marketo home">
            MARKETO<span className="text-[#FF4F00]">.</span>
          </a>
          <nav className="flex items-center gap-3" aria-label="Main">
            <Link
              to="/login"
              data-testid="nav-login"
              className="px-3 py-2 text-sm font-medium transition-colors hover:text-[#FF4F00]"
            >
              Login
            </Link>
            <Link
              to="/register"
              data-testid="nav-register"
              className="border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(255,79,0,1)]"
            >
              Become a Seller
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="relative overflow-hidden border-b border-[#0A0A0A]">
          <div className="mx-auto grid max-w-7xl grid-cols-1 gap-12 px-5 py-16 md:px-10 md:py-24 lg:grid-cols-12 lg:items-center">
            <div className="mk-in lg:col-span-7">
              <p className="mb-5 inline-block border border-[#0A0A0A] bg-white px-3 py-1 text-xs font-bold uppercase tracking-widest">
                0% commission marketplace
              </p>
              <h1 className="mk-head text-4xl font-black leading-[0.95] tracking-tighter sm:text-5xl lg:text-6xl">
                Open a shop.<br />
                Share your link.<br />
                <span className="text-[#FF4F00]">Keep every rupee.</span>
              </h1>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-[#525252] md:text-lg">
                Marketo gives anyone a real storefront at <span className="font-semibold text-[#0A0A0A]">marketo.com/your-name</span> in
                minutes. Buyers pay straight into your own Razorpay account — we never hold your money or take a cut.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  to="/register"
                  data-testid="hero-start-selling-btn"
                  className="group inline-flex items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-7 py-4 text-base font-bold text-white transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                >
                  Start Selling
                  <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>
                <a
                  href="#how-it-works"
                  data-testid="hero-how-it-works-link"
                  className="inline-flex items-center justify-center border-2 border-[#0A0A0A] bg-white px-7 py-4 text-base font-bold transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                >
                  See how it works
                </a>
              </div>
              <p className="mt-4 text-sm text-[#525252]">Free to start · No card required</p>
            </div>

            <div className="mk-in lg:col-span-5">
              <div className="relative">
                <img
                  src={STEPS[0].img}
                  alt={STEPS[0].alt}
                  width="800"
                  height="600"
                  loading="eager"
                  decoding="async"
                  className="w-full border-2 border-[#0A0A0A] object-cover grayscale"
                />
                <div className="absolute -bottom-6 -left-4 hidden border-2 border-[#0A0A0A] bg-white p-4 shadow-[6px_6px_0px_0px_rgba(255,79,0,1)] sm:block">
                  <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">Paid out</p>
                  <p className="mk-head text-2xl font-black tracking-tighter">100%</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="how-it-works" className="border-b border-[#0A0A0A] bg-white" data-testid="how-it-works-section">
          <div className="mx-auto max-w-7xl px-5 py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-3xl font-black tracking-tighter sm:text-4xl">
              Three steps to your first sale
            </h2>
            <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <article
                  key={s.n}
                  data-testid={`step-card-${i + 1}`}
                  className="mk-in group border-2 border-[#0A0A0A] bg-[#FAFAFA] transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                  style={{ animationDelay: `${i * 90}ms` }}
                >
                  <img
                    src={s.img}
                    alt={s.alt}
                    width="800"
                    height="450"
                    loading="lazy"
                    decoding="async"
                    className="h-44 w-full border-b-2 border-[#0A0A0A] object-cover grayscale transition-all duration-300 group-hover:grayscale-0"
                  />
                  <div className="p-7">
                    <div className="flex items-center gap-3">
                      <span className="mk-head text-sm font-black text-[#FF4F00]">{s.n}</span>
                      <s.icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h3 className="mk-head mt-3 text-lg font-extrabold tracking-tight md:text-lg">{s.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[#525252]">{s.desc}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* WHY MARKETO */}
        <section id="why-marketo" className="border-b border-[#0A0A0A]" data-testid="why-marketo-section">
          <div className="mx-auto max-w-7xl px-5 py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-3xl font-black tracking-tighter sm:text-4xl">
              Why sellers pick Marketo
            </h2>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-[#525252]">
              Most marketplaces charge you for the privilege of selling and sit on your money. We do neither.
            </p>
            <dl className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {REASONS.map((r, i) => (
                <div
                  key={r.title}
                  data-testid={`reason-card-${i + 1}`}
                  className="mk-in border-2 border-[#0A0A0A] bg-white p-7 transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(255,79,0,1)]"
                  style={{ animationDelay: `${i * 70}ms` }}
                >
                  <r.icon className="h-6 w-6 text-[#FF4F00]" aria-hidden="true" />
                  <dt className="mk-head mt-5 text-3xl font-black tracking-tighter">{r.k}</dt>
                  <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">{r.title}</p>
                  <dd className="mt-3 text-sm leading-relaxed text-[#525252]">{r.desc}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* PREMIUM TEASER */}
        <section id="pricing" className="border-b border-[#0A0A0A] bg-white" data-testid="pricing-section">
          <div className="mx-auto max-w-7xl px-5 py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-3xl font-black tracking-tighter sm:text-4xl">
              Selling is free. Going ad-free is optional.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-[#525252]">
              Free shops carry small Marketo ads. Marketo Pro removes them — that subscription is the only thing we ever charge for.
            </p>
            <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
              {PLANS.map((p, i) => (
                <article
                  key={p.name}
                  data-testid={`plan-card-${i + 1}`}
                  className={`mk-in relative border-2 border-[#0A0A0A] p-7 transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] ${
                    p.dark ? "bg-[#0A0A0A] text-white" : "bg-[#FAFAFA]"
                  }`}
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  {p.badge && (
                    <span className="absolute -top-3 right-5 border-2 border-[#0A0A0A] bg-[#FF4F00] px-2 py-0.5 text-xs font-bold uppercase tracking-widest text-white">
                      {p.badge}
                    </span>
                  )}
                  <h3 className="mk-head text-base font-extrabold uppercase tracking-widest md:text-base">{p.name}</h3>
                  <p className="mk-head mt-4 text-4xl font-black tracking-tighter">
                    {p.price}
                    <span className={`ml-2 text-sm font-medium tracking-normal ${p.dark ? "text-neutral-400" : "text-[#525252]"}`}>
                      {p.period}
                    </span>
                  </p>
                  <p className={`mt-2 text-sm ${p.dark ? "text-neutral-300" : "text-[#525252]"}`}>{p.note}</p>
                  <ul className="mt-6 space-y-2">
                    {p.feats.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#FF4F00]" aria-hidden="true" />
                        <span className={p.dark ? "text-neutral-200" : "text-[#525252]"}>{f}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
            <Link
              to="/register"
              data-testid="pricing-cta-btn"
              className="mt-10 inline-flex items-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-7 py-4 text-base font-bold text-white transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
            >
              Start free <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </section>

        {/* SOCIAL PROOF PLACEHOLDER */}
        <section id="social-proof" className="border-b border-[#0A0A0A]" data-testid="social-proof-section">
          <div className="mx-auto max-w-7xl px-5 py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-3xl font-black tracking-tighter sm:text-4xl">
              Seller stories, coming soon
            </h2>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-[#525252]">
              We're new, so we'd rather leave this space honest and empty than fill it with invented quotes.
            </p>
            <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
              {["₹—", "—", "—"].map((v, i) => (
                <div
                  key={i}
                  data-testid={`stat-placeholder-${i + 1}`}
                  className="border-2 border-dashed border-neutral-300 bg-white p-6 text-center"
                >
                  <p className="mk-head text-3xl font-black tracking-tighter text-neutral-400">{v}</p>
                  <p className="mt-1 text-xs font-bold uppercase tracking-widest text-neutral-400">
                    {["Paid to sellers", "Shops open", "Orders delivered"][i]}
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  data-testid={`testimonial-placeholder-${i}`}
                  className="border-2 border-dashed border-neutral-300 bg-white p-7"
                >
                  <div className="h-2 w-2/3 bg-neutral-200" />
                  <div className="mt-3 h-2 w-full bg-neutral-200" />
                  <div className="mt-3 h-2 w-4/5 bg-neutral-200" />
                  <div className="mt-6 flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-neutral-200" />
                    <div>
                      <div className="h-2 w-24 bg-neutral-200" />
                      <p className="mt-2 text-xs uppercase tracking-widest text-neutral-400">Testimonial coming soon</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* VISIT A SHOP */}
        <section className="border-b border-[#0A0A0A] bg-white" data-testid="visit-shop-section">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-12 md:flex-row md:items-end md:px-10">
            <div className="md:flex-1">
              <h2 className="mk-head text-2xl font-black tracking-tighter">Already have a shop link?</h2>
              <p className="mt-2 text-sm text-[#525252]">Enter a store handle to visit that shop.</p>
            </div>
            <form
              className="flex w-full gap-3 md:w-auto"
              onSubmit={(e) => {
                e.preventDefault();
                if (slug.trim()) navigate(`/${slug.trim()}`);
              }}
            >
              <input
                data-testid="visit-slug-input"
                value={slug || ""}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="store-handle"
                aria-label="Store handle"
                className="w-full border-2 border-[#0A0A0A] bg-white px-4 py-3 text-sm outline-none transition-colors focus:border-[#FF4F00] md:w-64"
              />
              <button
                type="submit"
                data-testid="visit-shop-btn"
                className="border-2 border-[#0A0A0A] bg-[#0A0A0A] px-6 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(255,79,0,1)]"
              >
                Go
              </button>
            </form>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

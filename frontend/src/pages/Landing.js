import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, BadgeIndianRupee, Link2, Zap, Store, PackagePlus, Share2, Check, ChevronDown, Sparkles, ShieldCheck } from "lucide-react";
import SiteFooter from "@/components/SiteFooter";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const STEPS = [
  {
    n: "01",
    title: "Create your shop",
    desc: "Sign up, pick your handle, and your shop is live at stallwise.in/your-name.",
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
  { name: "Free", price: "₹0", period: "forever", note: "Shows Stall Wise ads on your shop", feats: ["Unlimited products", "0% commission", "Delivery OTP + dispute protection"], dark: false, badge: null },
  { name: "Pro Monthly", price: "₹149", period: "per month", note: "Ad-free shop page", feats: ["Everything in Free", "No ads on your shop", "Cancel anytime"], dark: false, badge: null },
  { name: "Pro Yearly", price: "₹999", period: "per year", note: "Ad-free, best value", feats: ["Everything in Pro Monthly", "Save ₹789 a year", "Priority support"], dark: true, badge: "Best value" },
];

const FAQS = [
  {
    q: "How does 0% commission work on Stall Wise?",
    a: "Stall Wise connects buyers directly to your own Razorpay payment account. We do not hold your money or deduct transaction fees from your sales. 100% of the sale amount goes directly to you.",
  },
  {
    q: "How fast do I receive payments from buyers?",
    a: "Because buyers pay into your own Razorpay Key ID/Secret, payments settle directly into your linked bank account per your standard Razorpay settlement schedule (usually T+1 or T+2 days, or instant settlements).",
  },
  {
    q: "What is my shop link?",
    a: "When you choose a unique store handle during onboarding, your storefront is instantly available at stallwise.in/your-handle. You can share this link on Instagram bios, WhatsApp groups, Facebook, and Twitter.",
  },
  {
    q: "How does the Delivery OTP feature protect sellers and buyers?",
    a: "When a customer places an order, a secure 6-digit delivery OTP is generated. When delivering the package, the buyer provides this OTP to verify physical receipt. This prevents false non-delivery disputes and provides confidence for both parties.",
  },
  {
    q: "Is Stall Wise mobile friendly?",
    a: "Yes! Both the seller dashboard and customer storefronts are 100% optimized for mobile browsers, with fast page loads, one-tap checkout, and seamless Web Share integration.",
  },
];

export default function Landing() {
  const [slug, setSlug] = useState("");
  const [openFaq, setOpenFaq] = useState(0);
  const navigate = useNavigate();

  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": FAQS.map((f) => ({
      "@type": "Question",
      "name": f.q,
      "acceptedAnswer": {
        "@type": "Answer",
        "text": f.a,
      },
    })),
  };

  useDocumentMeta({
    title: "Stall Wise | Zero-Commission Marketplace — Open Your Own Shop",
    description:
      "Open your own shop at stallwise.in/your-name, list products and get paid directly into your Razorpay account. 0% commission, free to start.",
    path: "/",
    schemaData: faqSchema,
    keywords: "zero commission marketplace, open online store India, sell products online, direct razorpay seller store, creator shop, stallwise",
  });

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="landing-page">
      <header className="sticky top-0 z-50 border-b border-[#0A0A0A] bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 md:px-10 md:py-4">
          <a href="/" className="mk-head text-lg font-black tracking-tighter sm:text-xl" data-testid="brand-logo" aria-label="Stall Wise home">
            STALL WISE<span className="text-[#FF4F00]">.</span>
          </a>
          <nav className="flex items-center gap-2 sm:gap-3" aria-label="Main">
            <Link
              to="/login"
              data-testid="nav-login"
              className="px-2.5 py-1.5 text-xs font-bold uppercase tracking-wider text-[#0A0A0A] transition-colors hover:text-[#FF4F00] sm:px-3 sm:py-2 sm:text-sm"
            >
              Login
            </Link>
            <Link
              to="/register"
              data-testid="nav-register"
              className="border-2 border-[#0A0A0A] bg-[#0A0A0A] px-3 py-1.5 text-xs font-black uppercase tracking-wider text-white transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(255,79,0,1)] sm:px-4 sm:py-2 sm:text-sm"
            >
              Become a Seller
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="relative overflow-hidden border-b border-[#0A0A0A]">
          <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 px-4 py-12 sm:px-6 sm:py-16 md:px-10 md:py-24 lg:grid-cols-12 lg:items-center">
            <div className="mk-in lg:col-span-7">
              <div className="mb-4 inline-flex items-center gap-2 border border-[#0A0A0A] bg-white px-3 py-1 text-xs font-bold uppercase tracking-widest sm:mb-5">
                <Sparkles className="h-3.5 w-3.5 text-[#FF4F00]" />
                <span>0% commission marketplace</span>
              </div>
              <h1 className="mk-head text-3xl font-black leading-[1] tracking-tighter sm:text-5xl lg:text-6xl">
                Open a shop.<br />
                Share your link.<br />
                <span className="text-[#FF4F00]">Keep every rupee.</span>
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-relaxed text-[#525252] sm:mt-6 sm:text-base md:text-lg">
                Stall Wise gives anyone a real storefront at <span className="font-semibold text-[#0A0A0A]">stallwise.in/your-name</span> in
                minutes. Buyers pay straight into your own Razorpay account — we never hold your money or take a cut.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row sm:items-center">
                <Link
                  to="/register"
                  data-testid="hero-start-selling-btn"
                  className="group inline-flex min-h-[48px] items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-7 py-3.5 text-base font-bold text-white transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                >
                  Start Selling
                  <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>
                <a
                  href="#how-it-works"
                  data-testid="hero-how-it-works-link"
                  className="inline-flex min-h-[48px] items-center justify-center border-2 border-[#0A0A0A] bg-white px-7 py-3.5 text-base font-bold transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                >
                  See how it works
                </a>
              </div>
              <div className="mt-4 flex items-center gap-3 text-xs text-[#525252] sm:text-sm">
                <span className="flex items-center gap-1 font-medium"><ShieldCheck className="h-4 w-4 text-[#0B5227]" /> Free to start</span>
                <span>·</span>
                <span>No credit card required</span>
              </div>
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
                  className="w-full border-2 border-[#0A0A0A] object-cover grayscale aspect-4/3 sm:aspect-auto"
                />
                <div className="absolute -bottom-4 -left-3 border-2 border-[#0A0A0A] bg-white p-3 shadow-[4px_4px_0px_0px_rgba(255,79,0,1)] sm:-bottom-6 sm:-left-4 sm:p-4 sm:shadow-[6px_6px_0px_0px_rgba(255,79,0,1)]">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[#525252] sm:text-xs">Paid out</p>
                  <p className="mk-head text-xl font-black tracking-tighter sm:text-2xl">100%</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="how-it-works" className="border-b border-[#0A0A0A] bg-white" data-testid="how-it-works-section">
          <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-2xl font-black tracking-tighter sm:text-3xl md:text-4xl">
              Three steps to your first sale
            </h2>
            <div className="mt-8 grid grid-cols-1 gap-6 sm:mt-12 md:grid-cols-3">
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
                  <div className="p-5 sm:p-7">
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

        {/* WHY STALL WISE */}
        <section id="why-stall-wise" className="border-b border-[#0A0A0A]" data-testid="why-marketo-section">
          <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-2xl font-black tracking-tighter sm:text-3xl md:text-4xl">
              Why sellers pick Stall Wise
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#525252] sm:mt-4 sm:text-base">
              Most marketplaces charge you for the privilege of selling and sit on your money. We do neither.
            </p>
            <dl className="mt-8 grid grid-cols-1 gap-5 sm:mt-12 sm:grid-cols-2 lg:grid-cols-4">
              {REASONS.map((r, i) => (
                <div
                  key={r.title}
                  data-testid={`reason-card-${i + 1}`}
                  className="mk-in border-2 border-[#0A0A0A] bg-white p-5 transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(255,79,0,1)] sm:p-7"
                  style={{ animationDelay: `${i * 70}ms` }}
                >
                  <r.icon className="h-6 w-6 text-[#FF4F00]" aria-hidden="true" />
                  <dt className="mk-head mt-4 text-2xl font-black tracking-tighter sm:mt-5 sm:text-3xl">{r.k}</dt>
                  <p className="text-xs font-bold uppercase tracking-widest text-[#525252]">{r.title}</p>
                  <dd className="mt-2 text-sm leading-relaxed text-[#525252] sm:mt-3">{r.desc}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* PRICING */}
        <section id="pricing" className="border-b border-[#0A0A0A] bg-white" data-testid="pricing-section">
          <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 md:px-10 md:py-24">
            <h2 className="mk-head max-w-2xl text-2xl font-black tracking-tighter sm:text-3xl md:text-4xl">
              Selling is free. Going ad-free is optional.
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-[#525252] sm:mt-4 sm:text-base">
              Free shops carry small Stall Wise ads. Stall Wise Pro removes them — that subscription is the only thing we ever charge for.
            </p>
            <div className="mt-8 grid grid-cols-1 gap-6 sm:mt-12 md:grid-cols-3">
              {PLANS.map((p, i) => (
                <article
                  key={p.name}
                  data-testid={`plan-card-${i + 1}`}
                  className={`mk-in relative border-2 border-[#0A0A0A] p-5 transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] sm:p-7 ${
                    p.dark ? "bg-[#0A0A0A] text-white" : "bg-[#FAFAFA]"
                  }`}
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  {p.badge && (
                    <span className="absolute -top-3 right-5 border-2 border-[#0A0A0A] bg-[#FF4F00] px-2 py-0.5 text-xs font-bold uppercase tracking-widest text-white">
                      {p.badge}
                    </span>
                  )}
                  <h3 className="mk-head text-base font-extrabold uppercase tracking-widest">{p.name}</h3>
                  <p className="mk-head mt-4 text-3xl font-black tracking-tighter sm:text-4xl">
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
            <div className="mt-8 sm:mt-10">
              <Link
                to="/register"
                data-testid="pricing-cta-btn"
                className="inline-flex min-h-[48px] items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-7 py-3.5 text-base font-bold text-white transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
              >
                Start free <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </section>

        {/* FAQ SECTION (SEO + Mobile conversion) */}
        <section id="faqs" className="border-b border-[#0A0A0A] bg-[#FAFAFA]" data-testid="faq-section">
          <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-16 md:px-10 md:py-24">
            <div className="text-center sm:text-left">
              <span className="text-xs font-bold uppercase tracking-widest text-[#FF4F00]">Common questions</span>
              <h2 className="mk-head mt-2 text-2xl font-black tracking-tighter sm:text-3xl md:text-4xl">
                Frequently Asked Questions
              </h2>
            </div>
            <div className="mt-8 space-y-3 sm:mt-10">
              {FAQS.map((f, idx) => {
                const isOpen = openFaq === idx;
                return (
                  <div
                    key={idx}
                    className="border-2 border-[#0A0A0A] bg-white transition-all"
                  >
                    <button
                      type="button"
                      onClick={() => setOpenFaq(isOpen ? -1 : idx)}
                      className="flex w-full min-h-[52px] items-center justify-between gap-4 p-4 text-left font-bold text-[#0A0A0A] sm:p-5"
                      aria-expanded={isOpen}
                    >
                      <span className="text-sm sm:text-base">{f.q}</span>
                      <ChevronDown
                        className={`h-5 w-5 shrink-0 text-[#525252] transition-transform duration-200 ${
                          isOpen ? "rotate-180 text-[#FF4F00]" : ""
                        }`}
                      />
                    </button>
                    {isOpen && (
                      <div className="border-t border-[#E5E5E5] px-4 py-4 text-sm leading-relaxed text-[#525252] sm:px-5 sm:py-5 sm:text-base">
                        {f.a}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* VISIT A SHOP */}
        <section className="border-b border-[#0A0A0A] bg-white" data-testid="visit-shop-section">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-10 sm:px-6 sm:py-12 md:flex-row md:items-end md:px-10">
            <div className="md:flex-1">
              <h2 className="mk-head text-xl font-black tracking-tighter sm:text-2xl">Already have a shop link?</h2>
              <p className="mt-1 text-sm text-[#525252]">Enter a store handle to visit that shop.</p>
            </div>
            <form
              className="flex w-full flex-col gap-2 sm:flex-row sm:gap-3 md:w-auto"
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
                className="w-full border-2 border-[#0A0A0A] bg-white px-4 py-3 text-base outline-none transition-colors focus:border-[#FF4F00] sm:text-sm md:w-64"
              />
              <button
                type="submit"
                data-testid="visit-shop-btn"
                className="min-h-[44px] border-2 border-[#0A0A0A] bg-[#0A0A0A] px-6 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(255,79,0,1)]"
              >
                Visit Shop
              </button>
            </form>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

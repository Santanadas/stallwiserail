import { Link } from "react-router-dom";
import StaticPage from "@/components/StaticPage";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const H2 = ({ children }) => (
  <h2 className="mk-head text-lg font-extrabold tracking-tight text-[#0A0A0A]">{children}</h2>
);

const FAQ = [
  {
    q: "How much does it cost to sell on Stall Wise?",
    a: "Opening a shop is free. On the Free Plan the platform takes a 10% commission on each completed sale. Stall Wise Pro is ₹199/month or ₹1,499/year and removes the ads shown on your storefront.",
  },
  {
    q: "When do I get paid?",
    a: "As soon as the buyer's payment is captured. Payments are split at the gateway using Razorpay Route, so your share settles to your own bank account — Stall Wise never holds your money and there is no manual withdrawal step.",
  },
  {
    q: "Do I need a GST number or a registered company?",
    a: "No. You onboard as an individual or a business, and provide the bank account you want settlements paid into. Razorpay verifies the account before the first payout.",
  },
  {
    q: "Can I offer cash on delivery?",
    a: "Yes, per product. Enable cash on delivery on the items you're willing to deliver in person, and buyers will only see the option when every item in their cart accepts it. You collect the cash at handover and confirm delivery with the buyer's code.",
  },
  {
    q: "What payment methods can buyers use?",
    a: "UPI, debit and credit cards, netbanking and wallets through Razorpay checkout, plus cash on delivery where you've enabled it.",
  },
  {
    q: "How do I know an order was really delivered?",
    a: "When you mark an order shipped, the buyer is emailed a six-digit delivery code. You enter that code at handover to confirm delivery, which starts the acceptance window you set for your store.",
  },
];

export default function SellOnline() {
  useDocumentMeta({
    title: "How to Sell Online in India | Start a Shop on Stall Wise",
    description:
      "A practical guide to selling online in India: set up a storefront, accept UPI, cards and cash on delivery, and get paid straight into your bank account.",
    path: "/sell-online",
    schemaData: {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: FAQ.map((f) => ({
        "@type": "Question",
        name: f.q,
        acceptedAnswer: { "@type": "Answer", text: f.a },
      })),
    },
  });

  return (
    <StaticPage
      testId="sell-online-page"
      title="How to sell online in India"
      description="What it actually takes to go from a few products to a working online shop — and how payouts, delivery and fees work on Stall Wise."
    >
      <section>
        <H2>1. Decide what you're selling and how you'll price it</H2>
        <p className="mt-2">
          Start with the products you can reliably make or restock. For each one you'll need a title,
          a price in rupees, a short description and at least one clear photo. If an item comes in
          sizes, colours or materials, set those up as variants with their own price difference and
          stock count rather than as separate listings — buyers get one page to choose from, and your
          stock stays accurate.
        </p>
      </section>

      <section>
        <H2>2. Claim your shop link</H2>
        <p className="mt-2">
          Your storefront lives at <span className="font-mono font-bold">stallwise.in/your-name</span>.
          Pick the handle carefully: it's permanent, so existing links, QR codes and anything you've
          printed keep working. Every product also gets its own page at{" "}
          <span className="font-mono font-bold">stallwise.in/your-name/product-name</span>, which is
          what people find when they search for that specific item.
        </p>
      </section>

      <section>
        <H2>3. Connect the bank account you want to be paid into</H2>
        <p className="mt-2">
          Stall Wise uses Razorpay Route. You're onboarded as a linked account under the platform, and
          your bank details are registered for settlement. Once Razorpay finishes verifying the
          account, each buyer payment is split at the gateway: your share goes to your bank, the
          platform commission goes to Stall Wise. There's no holding period and no withdrawal request
          to remember.
        </p>
      </section>

      <section>
        <H2>4. Choose how buyers can pay</H2>
        <p className="mt-2">
          Every product carries its own payment settings. Online payment covers UPI, cards, netbanking
          and wallets. Cash on delivery is opt-in per product — sensible if you deliver locally, less
          so if you post things across the country. A buyer only sees cash on delivery if every item
          in their cart accepts it, so you're never committed to a COD run for something you meant to
          ship.
        </p>
      </section>

      <section>
        <H2>5. Fulfil the order and confirm delivery</H2>
        <p className="mt-2">
          A paid order appears in your dashboard ready to ship. Marking it shipped emails the buyer a
          six-digit delivery code. When you hand the order over, you enter that code to confirm
          delivery — proof for both sides that the item actually arrived. That starts the acceptance
          window you set for your store, after which the order completes automatically.
        </p>
      </section>

      <section>
        <H2>6. Share the link, because nobody finds a new shop by accident</H2>
        <p className="mt-2">
          Your shop and each product page are indexable by search engines and preview properly when
          shared on WhatsApp, Instagram or anywhere else. Put the link in your bio, print the QR code
          from your dashboard for markets and packaging, and send it directly to customers who've
          bought from you before. Search traffic follows the products, so the more specific your
          product titles and descriptions, the more likely someone searching for exactly that thing
          finds you.
        </p>
      </section>

      <section>
        <H2>Frequently asked questions</H2>
        <dl className="mt-4 space-y-5">
          {FAQ.map((f) => (
            <div key={f.q}>
              <dt className="font-bold text-[#0A0A0A]">{f.q}</dt>
              <dd className="mt-1.5 text-[#525252]">{f.a}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="border-2 border-[#0A0A0A] bg-white p-6">
        <H2>Ready to open your shop?</H2>
        <p className="mt-2 text-[#525252]">
          Setting up takes a few minutes. You can list your first product before connecting a bank
          account — you'll just need it in place before your first payout.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            to="/register"
            className="border-2 border-[#0A0A0A] bg-[#0A0A0A] px-5 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00]"
          >
            Open your shop
          </Link>
          <Link
            to="/shops"
            className="border-2 border-[#0A0A0A] bg-white px-5 py-2.5 text-sm font-bold transition-transform hover:-translate-y-0.5"
          >
            See other shops
          </Link>
        </div>
      </section>
    </StaticPage>
  );
}

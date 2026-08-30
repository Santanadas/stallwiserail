import StaticPage from "@/components/StaticPage";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const H2 = ({ children }) => <h2 className="mk-head text-lg font-extrabold tracking-tight text-[#0A0A0A] md:text-lg">{children}</h2>;

export default function About() {
  useDocumentMeta({
    title: "About Stall Wise | Direct-Payout Marketplace for Small Sellers",
    description:
      "Stall Wise lets anyone open an online shop at stallwise.in/your-name, list products and get paid directly into their linked bank account.",
    path: "/about",
    schemaType: "AboutPage",
  });
  return (
    <StaticPage
      testId="about-page"
      title="About Stall Wise"
      description="A marketplace that gets out of the way of the people doing the selling."
    >
      <section>
        <H2>Why we built it</H2>
        <p className="mt-2">
          Most marketplaces hold your money for days, charge hidden fees, and make sellers request manual payouts. For
          someone selling handmade candles or a few t-shirts a week, that model eats margin and patience. Stall Wise provides
          transparent pricing and direct, automated bank settlements via Razorpay.
        </p>
      </section>
      <section>
        <H2>How it works</H2>
        <p className="mt-2">
          Every seller gets a shop page at <strong>stallwise.in/your-handle</strong>. You add products with options like size and
          colour, share your link, and buyers check out through your own Razorpay account. Deliveries are confirmed with a
          one-time code so both sides know the order actually arrived.
        </p>
      </section>
      <section>
        <H2>How we make money</H2>
        <p className="mt-2">
          Stall Wise offers two flexible options: (1) Free Plan with a transparent 10% platform commission on completed orders, or (2) Stall Wise Pro (₹199/month or ₹1,499/year) with 0% platform commission, allowing active merchants to keep 100% of their earnings.
        </p>
      </section>
    </StaticPage>
  );
}

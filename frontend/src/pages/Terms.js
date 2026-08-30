import StaticPage from "@/components/StaticPage";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const H2 = ({ children }) => <h2 className="mk-head text-lg font-extrabold tracking-tight text-[#0A0A0A] md:text-lg">{children}</h2>;

export default function Terms() {
  useDocumentMeta({
    title: "Terms of Service | Stall Wise",
    description: "The terms that apply to sellers and buyers using Stall Wise shops, orders, delivery confirmation and Stall Wise Pro subscriptions.",
    path: "/terms",
    schemaType: "WebPage",
  });
  return (
    <StaticPage testId="terms-page" title="Terms of Service" description="Plain-language terms for using Stall Wise. Last updated June 2026.">
      <section>
        <H2>1. Your shop</H2>
        <p className="mt-2">
          You may open one shop per account and are responsible for everything you list. Illegal goods, counterfeits and anything
          you don't have the right to sell are not allowed and will get the shop removed.
        </p>
      </section>
      <section>
        <H2>2. Payments & Platform Commission</H2>
        <p className="mt-2">
          Stall Wise provides two monetization models for sellers: (a) Free Plan with a 10% platform commission on completed sales, or (b) Stall Wise Pro with 0% platform commission. Payouts are settled directly to the seller's linked bank account via Razorpay.
        </p>
      </section>
      <section>
        <H2>3. Delivery and disputes</H2>
        <p className="mt-2">
          Orders move through placed, paid, shipped and delivered states. Delivery is confirmed with a one-time code shared with
          the buyer. Buyers may raise a dispute within the stated dispute window; once that window closes the order is final and no
          refund can be requested through Stall Wise.
        </p>
      </section>
      <section>
        <H2>4. Stall Wise Pro Subscription</H2>
        <p className="mt-2">
          Stall Wise Pro (₹199/month or ₹1,499/year) eliminates all platform commissions (0% commission) and enables verified pro merchant features. Subscriptions renew until cancelled and can be managed directly in the merchant dashboard.
        </p>
      </section>
      <section>
        <H2>5. Changes</H2>
        <p className="mt-2">We may update these terms; continued use of Stall Wise means you accept the current version.</p>
      </section>
    </StaticPage>
  );
}

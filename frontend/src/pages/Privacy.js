import StaticPage from "@/components/StaticPage";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const H2 = ({ children }) => <h2 className="mk-head text-lg font-extrabold tracking-tight text-[#0A0A0A] md:text-lg">{children}</h2>;

export default function Privacy() {
  useDocumentMeta({
    title: "Privacy Policy | Stall Wise",
    description: "What data Stall Wise collects from sellers and buyers, how payment credentials are encrypted, and how to request deletion.",
    path: "/privacy",
    schemaType: "WebPage",
  });
  return (
    <StaticPage testId="privacy-page" title="Privacy Policy" description="What we collect, why, and what we never do with it. Last updated June 2026.">
      <section>
        <H2>What we collect</H2>
        <p className="mt-2">
          Account details (name, email), shop details, product listings, and order records. For buyers we store the order and the
          contact details needed to fulfil and confirm delivery.
        </p>
      </section>
      <section>
        <H2>Payment credentials</H2>
        <p className="mt-2">
          Sellers connect their own Razorpay account. The secret key is encrypted with AES-256 before it is stored and is only
          decrypted server-side at the moment an order is created. We never display it back to you and never share it.
        </p>
      </section>
      <section>
        <H2>Email</H2>
        <p className="mt-2">
          We send transactional email only — new order alerts and delivery one-time codes. No marketing email without your opt-in.
        </p>
      </section>
      <section>
        <H2>Your control</H2>
        <p className="mt-2">
          You can ask us to export or delete your account data at any time by writing to the address on our contact page. We do not
          sell personal data to anyone.
        </p>
      </section>
    </StaticPage>
  );
}

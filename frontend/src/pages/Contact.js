import StaticPage from "@/components/StaticPage";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const H2 = ({ children }) => <h2 className="mk-head text-lg font-extrabold tracking-tight text-[#0A0A0A] md:text-lg">{children}</h2>;

export default function Contact() {
  useDocumentMeta({
    title: "Contact Marketo | Seller Support",
    description: "Reach the Marketo team about seller accounts, payments, order disputes or Marketo Pro billing.",
    path: "/contact",
    schemaType: "ContactPage",
  });
  return (
    <StaticPage testId="contact-page" title="Contact us" description="Real replies from a small team, usually within a working day.">
      <section>
        <H2>Email</H2>
        <p className="mt-2">
          <a href="mailto:bongsharnipan123@gmail.com" data-testid="contact-email-link" className="font-semibold text-[#FF4F00] underline">
            bongsharnipan123@gmail.com
          </a>
        </p>
      </section>
      <section>
        <H2>What to include</H2>
        <p className="mt-2">
          For order issues, send the order ID and your shop handle. For payment problems, tell us whether the failure happened at
          checkout or at payout so we can point at the right side of the Razorpay flow.
        </p>
      </section>
      <section>
        <H2>Disputes</H2>
        <p className="mt-2">
          Raise disputes from the order page inside the dispute window — that keeps the record attached to the order. Email us only
          if the page won't let you.
        </p>
      </section>
    </StaticPage>
  );
}

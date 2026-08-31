import { Link } from "react-router-dom";

const LINKS = [
  { to: "/shops", label: "Browse shops" },
  { to: "/sell-online", label: "Sell online" },
  { to: "/about", label: "About" },
  { to: "/terms", label: "Terms" },
  { to: "/privacy", label: "Privacy" },
  { to: "/contact", label: "Contact" },
];

export default function SiteFooter() {
  return (
    <footer className="bg-neutral-900 text-white" data-testid="site-footer">
      <div className="mx-auto max-w-7xl px-5 py-16 md:px-10 md:py-20">
        <p className="mk-head text-4xl font-black leading-[0.95] tracking-tighter sm:text-5xl lg:text-6xl">
          Build your <span className="text-[#FF4F00]">own</span> shop.
        </p>
        <Link
          to="/register"
          data-testid="footer-start-selling-btn"
          className="mt-8 inline-flex border-2 border-white bg-transparent px-7 py-4 text-base font-bold text-white transition-colors hover:bg-white hover:text-[#0A0A0A]"
        >
          Start Selling
        </Link>

        <div className="mt-16 flex flex-col gap-6 border-t border-neutral-700 pt-8 md:flex-row md:items-center md:justify-between">
          <nav className="flex flex-wrap gap-6" aria-label="Footer">
            {LINKS.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                data-testid={`footer-link-${l.label.toLowerCase()}`}
                className="text-sm text-neutral-300 transition-colors hover:text-[#FF4F00]"
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <p className="text-sm text-neutral-500">© {new Date().getFullYear()} Stall Wise. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}

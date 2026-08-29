import { Link } from "react-router-dom";
import SiteFooter from "@/components/SiteFooter";

export default function StaticPage({ title, description, children, testId }) {
  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid={testId}>
      <header className="border-b border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-10">
          <Link to="/" className="mk-head text-xl font-black tracking-tighter" data-testid="static-brand-logo">
            STALL WISE<span className="text-[#FF4F00]">.</span>
          </Link>
          <Link
            to="/register"
            data-testid="static-nav-register"
            className="border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(255,79,0,1)]"
          >
            Start Selling
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-16 md:px-10 md:py-24">
        <h1 className="mk-head text-4xl font-black tracking-tighter sm:text-5xl">{title}</h1>
        <p className="mt-4 text-base leading-relaxed text-[#525252] md:text-lg">{description}</p>
        <div className="mt-10 space-y-6 text-sm leading-relaxed text-[#404040]">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}

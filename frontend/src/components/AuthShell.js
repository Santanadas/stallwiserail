import { Link } from "react-router-dom";
import { Check } from "lucide-react";

const POINTS = ["Direct payouts to your bank account", "Verified Delivery OTP security", "Your own shop link in minutes"];

export const AuthField = ({ label, value, ...props }) => (
  <label className="block">
    <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{label}</span>
    <input
      value={value ?? ""}
      {...props}
      className="mt-2 w-full border-2 border-[#0A0A0A] bg-white px-4 py-3 text-sm outline-none transition-colors placeholder:text-neutral-400 focus:border-[#FF4F00]"
    />
  </label>
);

export const AuthSubmit = ({ children, ...props }) => (
  <button
    {...props}
    className="w-full border-2 border-[#0A0A0A] bg-[#FF4F00] px-6 py-3.5 text-base font-bold text-white transition-transform hover:-translate-y-0.5 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-none"
  >
    {children}
  </button>
);

export const AuthAlert = ({ tone = "error", children, ...props }) => (
  <p
    {...props}
    role={tone === "error" ? "alert" : "status"}
    className={`border-2 px-4 py-3 text-sm font-medium ${
      tone === "error" ? "border-[#0A0A0A] bg-[#FFE9E0] text-[#8A2200]" : "border-[#0A0A0A] bg-[#E6F6EC] text-[#0B5227]"
    }`}
  >
    {children}
  </p>
);

export default function AuthShell({ title, subtitle, children, testId }) {
  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A] lg:grid lg:grid-cols-12" data-testid={testId}>
      <aside className="relative hidden bg-neutral-900 p-12 text-white lg:col-span-5 lg:flex lg:flex-col lg:justify-between xl:p-16">
        <Link to="/" className="mk-head text-xl font-black tracking-tighter" data-testid="auth-brand-logo">
          STALL WISE<span className="text-[#FF4F00]">.</span>
        </Link>
        <div>
          <p className="mk-head text-4xl font-black leading-[0.95] tracking-tighter xl:text-5xl">
            Your shop.<br />Your money.<br /><span className="text-[#FF4F00]">Your link.</span>
          </p>
          <ul className="mt-10 space-y-4">
            {POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3 text-sm text-neutral-300">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#FF4F00]" aria-hidden="true" />
                {p}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs uppercase tracking-widest text-neutral-500">stallwise.in/your-name</p>
      </aside>

      <div className="flex min-h-screen flex-col lg:col-span-7">
        <header className="border-b border-[#0A0A0A] bg-white lg:hidden">
          <div className="flex items-center justify-between px-5 py-4">
            <Link to="/" className="mk-head text-lg font-black tracking-tighter" data-testid="auth-brand-logo-mobile">
              STALL WISE<span className="text-[#FF4F00]">.</span>
            </Link>
            <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Direct Payouts</span>
          </div>
        </header>

        <main className="flex flex-1 items-center justify-center px-5 py-12 md:px-10 md:py-16">
          <div className="w-full max-w-md">
            <h1 className="mk-head text-3xl font-black tracking-tighter sm:text-4xl">{title}</h1>
            <p className="mt-3 text-sm leading-relaxed text-[#525252]">{subtitle}</p>
            <div className="mt-8 border-2 border-[#0A0A0A] bg-white p-6 shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] sm:p-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

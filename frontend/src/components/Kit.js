export const Panel = ({ title, action, children, testId }) => (
  <section
    data-testid={testId}
    className="border-2 border-[#0A0A0A] bg-white shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
  >
    <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-[#0A0A0A] bg-[#FAFAFA] px-5 py-3">
      <h2 className="mk-head text-base font-extrabold uppercase tracking-widest md:text-base">{title}</h2>
      {action}
    </div>
    <div className="p-5 sm:p-6">{children}</div>
  </section>
);

export const Field = ({ label, className = "", value, ...props }) => (
  <label className="block">
    {label && <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">{label}</span>}
    <input
      value={value ?? ""}
      {...props}
      className={`mt-1.5 w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-neutral-400 focus:border-[#FF4F00] ${className}`}
    />
  </label>
);

const VARIANTS = {
  primary: "border-[#0A0A0A] bg-[#FF4F00] text-white",
  dark: "border-[#0A0A0A] bg-[#0A0A0A] text-white",
  ghost: "border-[#0A0A0A] bg-white text-[#0A0A0A]",
  danger: "border-[#8A2200] bg-white text-[#8A2200]",
};

export const Btn = ({ variant = "ghost", className = "", children, ...props }) => (
  <button
    {...props}
    className={`inline-flex items-center justify-center gap-2 border-2 px-4 py-2.5 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-none ${VARIANTS[variant]} ${className}`}
  >
    {children}
  </button>
);

const STATUS_TONE = {
  placed: "bg-[#FFF4E0] text-[#7A4A00]",
  paid: "bg-[#E6F0FF] text-[#0B3B7A]",
  shipped: "bg-[#EDE6FF] text-[#3B1E7A]",
  delivered_pending_otp: "bg-[#FFF0E0] text-[#8A3E00]",
  delivered_confirmed: "bg-[#E6F6EC] text-[#0B5227]",
  completed: "bg-[#0A0A0A] text-white",
  disputed: "bg-[#FFE0E0] text-[#8A0000]",
};

export const StatusPill = ({ status, ...props }) => (
  <span
    {...props}
    className={`inline-block border border-[#0A0A0A] px-2 py-0.5 text-xs font-bold uppercase tracking-wider ${
      STATUS_TONE[status] || "bg-neutral-100 text-neutral-700"
    }`}
  >
    {String(status).replace(/_/g, " ")}
  </span>
);

export const Note = ({ tone = "info", children, ...props }) => (
  <p
    {...props}
    className={`border-2 border-[#0A0A0A] px-4 py-2.5 text-sm font-medium ${
      tone === "error"
        ? "bg-[#FFE9E0] text-[#8A2200]"
        : tone === "success"
          ? "bg-[#E6F6EC] text-[#0B5227]"
          : "bg-[#FFF4E0] text-[#7A4A00]"
    }`}
  >
    {children}
  </p>
);

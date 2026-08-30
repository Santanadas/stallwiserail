export const Panel = ({ title, action, subtitle, children, testId, className = "" }) => (
  <section
    data-testid={testId}
    className={`overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-sm transition-all hover:shadow-md ${className}`}
  >
    {(title || action) && (
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-100 bg-neutral-50/60 px-5 py-4 sm:px-6">
        <div>
          {title && (
            <h2 className="mk-head text-base font-black tracking-tight text-[#0A0A0A] sm:text-lg">
              {title}
            </h2>
          )}
          {subtitle && (
            <p className="mt-0.5 text-xs text-neutral-500 font-normal">
              {subtitle}
            </p>
          )}
        </div>
        {action}
      </div>
    )}
    <div className="p-5 sm:p-6">{children}</div>
  </section>
);

export const Field = ({ label, className = "", value, helper, ...props }) => (
  <label className="block">
    {label && (
      <span className="text-xs font-bold uppercase tracking-wider text-neutral-600 mb-1.5 block">
        {label}
      </span>
    )}
    <input
      value={value ?? ""}
      {...props}
      className={`w-full rounded-xl border border-neutral-200 bg-white px-3.5 py-2.5 text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10 ${className}`}
    />
    {helper && <span className="mt-1 text-xs text-neutral-400 block">{helper}</span>}
  </label>
);

const VARIANTS = {
  primary: "bg-[#FF4F00] text-white hover:bg-[#E04500] shadow-sm hover:shadow",
  dark: "bg-neutral-900 text-white hover:bg-neutral-800 shadow-sm",
  ghost: "bg-neutral-50 border border-neutral-200 text-neutral-800 hover:bg-neutral-100",
  outline: "border border-neutral-300 bg-transparent text-neutral-800 hover:bg-neutral-50",
  danger: "bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100",
  emerald: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
};

export const Btn = ({ variant = "ghost", className = "", children, ...props }) => (
  <button
    {...props}
    className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs sm:text-sm font-bold transition-all disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.98] ${VARIANTS[variant] || VARIANTS.ghost} ${className}`}
  >
    {children}
  </button>
);

const STATUS_CONFIG = {
  placed: {
    bg: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
    label: "Order Placed",
  },
  paid: {
    bg: "bg-blue-50 text-blue-700 border-blue-200",
    dot: "bg-blue-500",
    label: "Paid • Ready to Ship",
  },
  shipped: {
    bg: "bg-purple-50 text-purple-700 border-purple-200",
    dot: "bg-purple-500",
    label: "Shipped",
  },
  delivered_pending_otp: {
    bg: "bg-orange-50 text-orange-700 border-orange-200",
    dot: "bg-orange-500 animate-pulse",
    label: "Awaiting OTP Handover",
  },
  delivered_confirmed: {
    bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dot: "bg-emerald-500",
    label: "Delivered (OTP Verified)",
  },
  completed: {
    bg: "bg-neutral-900 text-white border-neutral-900",
    dot: "bg-emerald-400",
    label: "Completed",
  },
  disputed: {
    bg: "bg-rose-50 text-rose-700 border-rose-200",
    dot: "bg-rose-500",
    label: "Disputed",
  },
};

export const StatusPill = ({ status, className = "", ...props }) => {
  const conf = STATUS_CONFIG[status] || {
    bg: "bg-neutral-100 text-neutral-700 border-neutral-200",
    dot: "bg-neutral-400",
    label: String(status || "").replace(/_/g, " "),
  };

  return (
    <span
      {...props}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold tracking-tight shadow-2xs ${conf.bg} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${conf.dot}`} />
      <span>{conf.label}</span>
    </span>
  );
};

export const Note = ({ tone = "info", children, className = "", ...props }) => {
  const tones = {
    error: "bg-rose-50 border-rose-200 text-rose-800",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
    info: "bg-blue-50 border-blue-200 text-blue-800",
  };

  return (
    <div
      {...props}
      className={`rounded-xl border p-3.5 text-xs sm:text-sm font-medium ${tones[tone] || tones.info} ${className}`}
    >
      {children}
    </div>
  );
};

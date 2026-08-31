import { Link } from "react-router-dom";
import {
  Home, ShoppingBag, Package, Users, TrendingUp, CreditCard,
  Settings as SettingsIcon, Bell, Copy, Check, LogOut, ChevronsUpDown, ExternalLink,
} from "lucide-react";

/**
 * The seller console shell.
 *
 * Replaces the old horizontally-scrolling tab strip: nine destinations grouped
 * by what the seller is doing, so adding a section no longer costs horizontal
 * room. Orange is reserved for "needs action" — nothing decorative uses it.
 */

export const NAV_GROUPS = [
  {
    label: "Run the shop",
    items: [
      { id: "home", label: "Home", icon: Home },
      { id: "orders", label: "Orders", icon: ShoppingBag, badge: "toShip" },
      { id: "products", label: "Products", icon: Package, badge: "products" },
      { id: "customers", label: "Customers", icon: Users },
    ],
  },
  {
    label: "Grow",
    items: [{ id: "insights", label: "Insights", icon: TrendingUp }],
  },
  {
    label: "Money",
    items: [
      { id: "payouts", label: "Payouts", icon: CreditCard, badge: "bank" },
      { id: "settings", label: "Settings", icon: SettingsIcon },
    ],
  },
];

function Badge({ kind, counts }) {
  if (kind === "toShip") {
    const n = counts.toShip || 0;
    if (!n) return null;
    return <span className="rounded-full bg-[#FF4F00] px-1.5 py-0.5 text-[10px] font-black text-white">{n}</span>;
  }
  if (kind === "products") {
    const n = counts.products || 0;
    if (!n) return null;
    return <span className="rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-black text-neutral-500">{n}</span>;
  }
  if (kind === "bank" && counts.bankReady === false) {
    return <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />;
  }
  return null;
}

export default function Shell({
  store, user, active, onNav, counts = {}, onLogout, title, subtitle, action, children,
}) {
  const copy = async () => {
    if (!store?.slug) return;
    try {
      await navigator.clipboard.writeText(`https://stallwise.in/${store.slug}`);
      counts.onCopied?.();
    } catch { /* clipboard unavailable */ }
  };

  return (
    <div className="mk flex min-h-screen bg-[#FAFAFA]">
      {/* ---------------- Sidebar ---------------- */}
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col border-r border-neutral-200 bg-white lg:flex">
        <div className="flex items-center gap-2.5 border-b border-neutral-100 px-4 py-3.5">
          <div className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-[11px] bg-[#FF4F00] text-sm font-black text-white">
            {(store?.name || "SW").slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="mk-head truncate text-sm font-black tracking-tight text-[#0A0A0A]">
              {store?.name || "Your shop"}
            </div>
            <div className="truncate text-[11px] font-medium text-neutral-400">
              stallwise.in/{store?.slug || "…"}
            </div>
          </div>
          <ChevronsUpDown className="h-4 w-4 shrink-0 text-neutral-400" />
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2.5">
          {NAV_GROUPS.map((g) => (
            <div key={g.label}>
              <div className="px-2.5 pb-1.5 pt-3 text-[10px] font-bold uppercase tracking-[0.08em] text-neutral-400">
                {g.label}
              </div>
              {g.items.map((it) => {
                const Icon = it.icon;
                const on = active === it.id;
                return (
                  <button
                    key={it.id}
                    type="button"
                    data-testid={`nav-${it.id}`}
                    onClick={() => onNav(it.id)}
                    className={`flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2.5 text-[13px] transition-colors ${
                      on
                        ? "bg-[#FFF7ED] font-bold text-[#C43D00]"
                        : "font-semibold text-neutral-600 hover:bg-neutral-50"
                    }`}
                  >
                    <Icon className={`h-[17px] w-[17px] shrink-0 ${on ? "text-[#C43D00]" : "text-neutral-500"}`} />
                    <span className="flex-1 text-left">{it.label}</span>
                    <Badge kind={it.badge} counts={counts} />
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="border-t border-neutral-100 p-3">
          {!counts.isPro && (
            <div className="mb-2.5 flex flex-col gap-2.5 rounded-2xl bg-[#0A0A0A] p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-neutral-400">Free plan</span>
                <span className="text-[10px] font-bold text-[#FF7A3D]">
                  {Math.round((counts.commissionRate ?? 0.1) * 100)}% fee
                </span>
              </div>
              {counts.commissionThisMonth > 0 && (
                <p className="text-xs font-medium leading-snug text-neutral-200">
                  You paid <strong className="font-extrabold text-white">₹{counts.commissionThisMonth.toLocaleString("en-IN")}</strong> in commission this month.
                </p>
              )}
              <button
                type="button"
                onClick={() => onNav("payouts")}
                className="rounded-[10px] bg-[#FF4F00] py-2 text-xs font-extrabold text-white transition-colors hover:bg-[#E04500]"
              >
                Go Pro
              </button>
            </div>
          )}
          <button
            type="button"
            onClick={onLogout}
            data-testid="logout-btn"
            className="flex w-full items-center gap-2.5 rounded-[10px] px-2.5 py-2 text-[13px] font-semibold text-neutral-500 transition-colors hover:bg-neutral-50 hover:text-neutral-800"
          >
            <LogOut className="h-4 w-4" /> Log out
          </button>
        </div>
      </aside>

      {/* ---------------- Main ---------------- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-[64px] flex-wrap items-center justify-between gap-3 border-b border-neutral-200 bg-white px-4 py-3 sm:px-7">
          <div className="min-w-0">
            <h1 className="mk-head truncate text-lg font-black tracking-tight text-[#0A0A0A]">{title}</h1>
            {subtitle && <p className="mt-0.5 truncate text-xs font-medium text-neutral-500">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-2">
            {action}
            {store?.slug && (
              <>
                <button
                  type="button"
                  onClick={copy}
                  data-testid="copy-shop-url"
                  className="hidden h-9 items-center gap-1.5 rounded-[10px] border border-neutral-200 bg-white px-3 text-xs font-semibold text-neutral-600 transition-colors hover:bg-neutral-50 sm:flex"
                >
                  stallwise.in/{store.slug}
                  {counts.copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-neutral-400" />}
                </button>
                <Link
                  to={`/${store.slug}`}
                  className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50"
                  title="View your shop"
                >
                  <ExternalLink className="h-4 w-4" />
                </Link>
              </>
            )}
            <button
              type="button"
              onClick={() => onNav("orders")}
              className="relative flex h-9 w-9 items-center justify-center rounded-[10px] border border-neutral-200 bg-white text-neutral-600 transition-colors hover:bg-neutral-50"
              title="Things needing attention"
            >
              <Bell className="h-4 w-4" />
              {counts.needsAttention > 0 && (
                <span className="absolute right-1.5 top-1.5 h-[7px] w-[7px] rounded-full border-[1.5px] border-white bg-[#FF4F00]" />
              )}
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[#0A0A0A] text-[13px] font-black text-white">
              {(user?.name || user?.email || "S").slice(0, 2).toUpperCase()}
            </div>
          </div>
        </header>

        {/* Mobile nav — the sidebar is desktop-only */}
        <div className="flex gap-1 overflow-x-auto border-b border-neutral-200 bg-white px-3 py-2 lg:hidden">
          {NAV_GROUPS.flatMap((g) => g.items).map((it) => (
            <button
              key={it.id}
              type="button"
              onClick={() => onNav(it.id)}
              className={`shrink-0 rounded-[10px] px-3 py-2 text-xs font-bold transition-colors ${
                active === it.id ? "bg-[#FFF7ED] text-[#C43D00]" : "text-neutral-600"
              }`}
            >
              {it.label}
            </button>
          ))}
        </div>

        <main className="flex-1 px-4 py-6 sm:px-7">{children}</main>
      </div>
    </div>
  );
}

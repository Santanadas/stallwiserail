import { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import {
  ExternalLink,
  LogOut,
  Plus,
  Trash2,
  Landmark,
  ShieldCheck,
  ShieldOff,
  ChevronLeft,
  ChevronRight,
  Grid,
  List,
  Package,
  ShoppingBag,
  Share2,
  Check,
  Camera,
  Edit3,
  Sparkles,
  Layers,
  Settings,
  CreditCard,
  X,
  Store,
  QrCode,
  TrendingUp,
  DollarSign,
  ArrowUpRight,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Truck,
  Copy,
  ChevronDown,
  Percent,
  AlertTriangle,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Panel, Field, Btn, StatusPill, Note } from "@/components/Kit";
import ImageUpload, { fileUrl } from "@/components/ImageUpload";
import ProductEditor from "@/components/ProductEditor";
import StoreQrModal from "@/components/StoreQrModal";
import { useDocumentMeta } from "@/lib/useDocumentMeta";
import Shell from "@/components/dash/Shell";
import Assistant from "@/components/dash/Assistant";
import HomeSection from "@/components/dash/Home";
import InsightsSection from "@/components/dash/Insights";
import MoneySection from "@/components/dash/Money";
import CustomersSection from "@/components/dash/Customers";
import ShopSettings from "@/components/dash/ShopSettings";

/* ==========================================================================
   SETTINGS — shared bits
   ========================================================================== */
const SettingsCard = ({ title, description, children, footer, testId }) => (
  <section
    data-testid={testId}
    className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs"
  >
    <div className="border-b border-neutral-100 px-5 py-4 sm:px-6">
      <h3 className="mk-head text-sm font-black tracking-tight text-[#0A0A0A]">{title}</h3>
      {description && <p className="mt-0.5 text-xs leading-relaxed text-neutral-500">{description}</p>}
    </div>
    <div className="px-5 py-5 sm:px-6">{children}</div>
    {footer && <div className="border-t border-neutral-100 bg-neutral-50/60 px-5 py-3 sm:px-6">{footer}</div>}
  </section>
);

/* A label/value row for read-only account facts. */
const InfoRow = ({ label, value, children }) => (
  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-100 py-3 last:border-0 last:pb-0 first:pt-0">
    <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">{label}</span>
    {children || <span className="text-sm font-semibold text-[#0A0A0A] break-all">{value}</span>}
  </div>
);

/* ==========================================================================
   STORE SETTINGS SECTION
   ========================================================================== */
function StoreSection({ store, onChange, user, refreshUser }) {
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [baseline, setBaseline] = useState(null);
  const [copied, setCopied] = useState(false);

  // Snapshot the saved state so we can tell when there are unsaved edits.
  useEffect(() => {
    if (store && !baseline) {
      setBaseline({
        name: store.name || "",
        bio: store.bio || "",
        acceptanceWindowMinutes: String(store.acceptanceWindowMinutes ?? 120),
      });
    }
  }, [store, baseline]);

  const dirty =
    baseline &&
    (baseline.name !== (store?.name || "") ||
      baseline.bio !== (store?.bio || "") ||
      baseline.acceptanceWindowMinutes !== String(store?.acceptanceWindowMinutes ?? 120));

  if (!store) return null;

  const copyHandle = async () => {
    try {
      await navigator.clipboard.writeText(`https://stallwise.in/${store.slug}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const discard = () => {
    if (!baseline) return;
    onChange({ ...store, ...baseline, acceptanceWindowMinutes: Number(baseline.acceptanceWindowMinutes) }, true);
  };

  const save = async () => {
    setErr("");
    setSaved(false);
    setBusy(true);
    try {
      await api.put("/stores/me", {
        name: store?.name || "",
        bio: store?.bio || "",
        acceptanceWindowMinutes: Number(store?.acceptanceWindowMinutes || 120),
      });
      setBaseline({
        name: store?.name || "",
        bio: store?.bio || "",
        acceptanceWindowMinutes: String(store?.acceptanceWindowMinutes ?? 120),
      });
      setSaved(true);
      onChange();
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const setAvatar = async (val) => {
    if (!val) {
      try {
        await api.delete("/uploads/avatar");
      } catch (e) {
        console.error("Failed to remove avatar", e);
      }
    }
    await refreshUser?.();
  };

  const bioCount = (store?.bio || "").length;

  return (
    <div className="space-y-5" data-testid="store-panel">
      {/* ---------- Profile header ---------- */}
      <section className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs">
        <div className="h-20 bg-gradient-to-r from-[#FF4F00] via-orange-500 to-amber-400" />
        <div className="px-5 pb-5 sm:px-6">
          <div className="-mt-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex items-end gap-4">
              <div className="h-20 w-20 shrink-0 overflow-hidden rounded-2xl border-4 border-white bg-neutral-100 shadow-sm">
                {user?.avatar ? (
                  <img src={fileUrl(user.avatar)} alt="" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-neutral-900 text-lg font-black text-white">
                    {(store?.name || "SW").slice(0, 2).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="min-w-0 pb-1">
                <h2 className="mk-head truncate text-xl font-black tracking-tight text-[#0A0A0A]">
                  {store?.name || "My Store"}
                </h2>
                <button
                  type="button"
                  onClick={copyHandle}
                  className="mt-0.5 inline-flex items-center gap-1.5 font-mono text-xs text-neutral-500 transition-colors hover:text-[#FF4F00]"
                  title="Copy storefront link"
                >
                  stallwise.in/<span className="font-bold text-[#FF4F00]">{store?.slug}</span>
                  {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
            </div>
            {store?.slug && (
              <Link
                to={`/${store.slug}`}
                target="_blank"
                data-testid="store-shop-link"
                className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs font-bold text-neutral-800 transition-all hover:border-neutral-300 hover:bg-neutral-50 sm:self-auto"
              >
                View storefront <ExternalLink className="h-3.5 w-3.5 text-neutral-500" />
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* ---------- Brand ---------- */}
      <SettingsCard
        title="Brand"
        description="Your logo appears on the storefront, product cards and buyer receipts."
      >
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <ImageUpload
            value={user?.avatar}
            onChange={setAvatar}
            kind="avatar"
            shape="round"
            label="Upload logo"
            testId="store-avatar"
          />
          <p className="max-w-sm text-xs leading-relaxed text-neutral-500">
            Square image, 300×300px or larger. PNG or JPG.
          </p>
        </div>
      </SettingsCard>

      {/* ---------- Storefront ---------- */}
      <SettingsCard
        title="Storefront"
        description="What buyers read when they land on your shop."
      >
        <div className="space-y-5">
          <Field
            label="Store name"
            data-testid="store-name-edit"
            value={store?.name || ""}
            placeholder="e.g. Studio Craft Ceramics"
            onChange={(e) => onChange({ ...store, name: e.target.value }, true)}
            helper="Shown as your shop's heading."
          />

          <div>
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-600">Bio</span>
              <span className={`text-[11px] ${bioCount > 500 ? "text-rose-600" : "text-neutral-400"}`}>
                {bioCount}/500
              </span>
            </div>
            <textarea
              data-testid="store-bio-edit"
              rows={4}
              maxLength={500}
              placeholder="What makes your products special, packaging, shipping timelines…"
              value={store?.bio || ""}
              onChange={(e) => onChange({ ...store, bio: e.target.value }, true)}
              className="w-full rounded-xl border border-neutral-200 bg-white p-3.5 text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10"
            />
          </div>

          <div className="rounded-xl border border-neutral-200 bg-neutral-50/60 p-3.5">
            <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">Shop handle</span>
            <p className="mt-1 font-mono text-sm font-bold text-[#0A0A0A]">stallwise.in/{store?.slug}</p>
            <p className="mt-1 text-xs text-neutral-500">
              Your handle is permanent — it keeps existing links and QR codes working.
            </p>
          </div>
        </div>
      </SettingsCard>

      {/* ---------- Fulfilment ---------- */}
      <SettingsCard
        title="Fulfilment"
        description="How long buyers have to raise a dispute after you confirm delivery."
      >
        <div className="sm:max-w-xs">
          <Field
            label="Acceptance window (minutes)"
            data-testid="store-window-edit"
            type="number"
            min="1"
            value={store?.acceptanceWindowMinutes ?? 120}
            onChange={(e) => onChange({ ...store, acceptanceWindowMinutes: e.target.value }, true)}
            helper="Default 120. The order completes automatically once it passes."
          />
        </div>
      </SettingsCard>

      {err && <Note tone="error">{err}</Note>}

      {/* ---------- Sticky save bar ---------- */}
      <AnimatePresence>
        {(dirty || saved) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className="sticky bottom-4 z-30 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-800 bg-neutral-900 px-4 py-3 shadow-lg"
          >
            {saved && !dirty ? (
              <span className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
                <Check className="h-4 w-4" /> Changes saved
              </span>
            ) : (
              <>
                <span className="text-sm font-bold text-white">You have unsaved changes</span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={discard}
                    disabled={busy}
                    className="rounded-xl px-3 py-2 text-xs font-bold text-neutral-300 transition-colors hover:text-white disabled:opacity-50"
                  >
                    Discard
                  </button>
                  <Btn variant="primary" data-testid="store-save-btn" onClick={save} disabled={busy}>
                    {busy ? "Saving…" : "Save changes"}
                  </Btn>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ==========================================================================
   ACCOUNT SECTION
   ========================================================================== */
function AccountSection({ user, onLogout }) {
  const joined = (() => {
    try {
      return user?.created_at
        ? new Date(user.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
        : null;
    } catch {
      return null;
    }
  })();

  return (
    <SettingsCard
      title="Account"
      description="The login attached to this store."
      testId="account-panel"
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-neutral-500">Signing out won't affect your live storefront.</span>
          <Btn variant="danger" data-testid="account-logout-btn" onClick={onLogout}>
            <LogOut className="h-4 w-4" /> Log out
          </Btn>
        </div>
      }
    >
      <div>
        <InfoRow label="Email" value={user?.email || "—"} />
        <InfoRow
          label="Sign-in"
          value={user?.authProvider === "google" ? "Google" : "Email & password"}
        />
        {joined && <InfoRow label="Member since" value={joined} />}
        <InfoRow label="Plan">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold ${
              user?.subscriptionStatus === "active"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-neutral-200 bg-neutral-100 text-neutral-600"
            }`}
          >
            {user?.subscriptionStatus === "active" ? <><Sparkles className="h-3 w-3" /> Pro</> : "Free"}
          </span>
        </InfoRow>
      </div>
    </SettingsCard>
  );
}

/* ==========================================================================
   PAYMENT ROUTE & SETTLEMENT SECTION
   ========================================================================== */
const IFSC_RE = /^[A-Za-z]{4}0[A-Za-z0-9]{6}$/;
const ACCT_RE = /^\d{6,18}$/;

function RouteSection({ onChange }) {
  const [route, setRoute] = useState(null);
  const [form, setForm] = useState({
    legal_business_name: "",
    contact_name: "",
    phone: "",
    beneficiary_name: "",
    account_number: "",
    ifsc: "",
  });
  const [msg, setMsg] = useState("");
  const [msgTone, setMsgTone] = useState("error");
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/seller/route");
      setRoute(data?.connected ? data : null);
    } catch {}
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const validate = () => {
    if (!form.legal_business_name.trim()) return "Enter your legal / registered name.";
    if (!form.contact_name.trim()) return "Enter the primary contact name.";
    if (!/^\d{8,15}$/.test(form.phone.replace(/\D/g, ""))) return "Enter a valid phone number.";
    if (!form.beneficiary_name.trim()) return "Enter the bank account holder's name.";
    if (!ACCT_RE.test(form.account_number.trim())) return "Bank account number must be 6–18 digits.";
    if (!IFSC_RE.test(form.ifsc.trim())) return "That IFSC code doesn't look valid (e.g. HDFC0001234).";
    return null;
  };

  const connect = async () => {
    setMsg("");
    const err = validate();
    if (err) {
      setMsgTone("error");
      setMsg(err);
      return;
    }
    setBusy(true);
    try {
      const payload = {
        ...form,
        phone: form.phone.replace(/\D/g, ""),
        ifsc: form.ifsc.trim().toUpperCase(),
        account_number: form.account_number.trim(),
      };
      const { data } = await api.post("/seller/route/onboard", payload);
      setMsgTone("success");
      setMsg(
        data?.payoutsLive
          ? "Bank account linked. Razorpay is verifying it — payouts activate once verification completes."
          : "Bank details saved. Direct payouts will switch on once Razorpay Route finishes verification."
      );
      setForm({
        legal_business_name: "",
        contact_name: "",
        phone: "",
        beneficiary_name: "",
        account_number: "",
        ifsc: "",
      });
      setRoute(data?.connected ? data : null);
      onChange();
    } catch (e) {
      setMsgTone("error");
      setMsg(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    setMsg("");
    try {
      const { data } = await api.post("/seller/route/refresh");
      setRoute(data?.connected ? data : null);
    } catch (e) {
      setMsgTone("error");
      setMsg(formatApiError(e.response?.data?.detail));
    } finally {
      setRefreshing(false);
    }
  };

  const disconnect = async () => {
    // This used to say the money would settle to the platform. It does not:
    // checkout refuses an online payment it cannot forward, so disconnecting
    // takes the shop down to cash on delivery.
    if (confirm("Disconnect your bank? Your shop will only be able to take cash on delivery until you reconnect.")) {
      await api.delete("/seller/route");
      setRoute(null);
      onChange();
    }
  };

  const live = route?.payoutsLive;
  const settlementReady = ["activated", "active", "configured"].includes(
    String(route?.settlementStatus || "").toLowerCase()
  );

  return (
    <Panel
      title="Direct Bank Settlement & Razorpay Route"
      subtitle="Customer payments settle automatically to your verified bank account."
      testId="route-panel"
      action={
        <span
          data-testid="route-status"
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${
            route?.connected && settlementReady
              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
              : route?.connected
              ? "bg-amber-50 border-amber-200 text-amber-700"
              : "bg-neutral-100 border-neutral-200 text-neutral-600"
          }`}
        >
          {route?.connected && settlementReady ? (
            <>
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Payouts Active</span>
            </>
          ) : route?.connected ? (
            <>
              <Clock className="h-4 w-4 text-amber-600" />
              <span>Verifying</span>
            </>
          ) : (
            <>
              <ShieldOff className="h-4 w-4 text-neutral-400" />
              <span>Not Configured</span>
            </>
          )}
        </span>
      }
    >
      <div className="space-y-6">
        {/* Value Prop Banner */}
        <div className="flex items-start gap-4 rounded-2xl border border-blue-100 bg-gradient-to-r from-blue-50/70 via-indigo-50/40 to-transparent p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
            <Landmark className="h-5 w-5" />
          </div>
          <div>
            <h4 className="font-bold text-[#0A0A0A] text-sm">Automated Direct Bank Settlements</h4>
            <p className="mt-1 text-xs leading-relaxed text-neutral-600">
              Stall Wise is powered by Razorpay Route. When a customer pays, your share of the order is transferred straight to this linked bank account — no holding periods, no manual withdrawal requests. Razorpay runs its own bank-account verification before the first payout.
            </p>
          </div>
        </div>

        {route?.connected ? (
          <div className="rounded-2xl border border-neutral-200 bg-neutral-50/60 p-6" data-testid="route-connected-card">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-white p-4 border border-neutral-100 shadow-2xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">Linked Account</span>
                <p className="mt-1 font-mono text-sm font-bold text-[#0A0A0A]">••••{route.accountIdLast4}</p>
              </div>

              {route.bankLast4 && (
                <div className="rounded-xl bg-white p-4 border border-neutral-100 shadow-2xs">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">Bank Account</span>
                  <p className="mt-1 font-mono text-sm font-bold text-[#0A0A0A]">••••{route.bankLast4}</p>
                  {route.ifsc && <p className="mt-0.5 font-mono text-[11px] text-neutral-500">{route.ifsc}</p>}
                </div>
              )}

              <div className="rounded-xl bg-white p-4 border border-neutral-100 shadow-2xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">Settlement Status</span>
                <p className={`mt-1 font-bold capitalize text-sm ${settlementReady ? "text-emerald-600" : "text-amber-600"}`}>
                  {(route.settlementStatus || route.status || "pending").replace(/_/g, " ")}
                </p>
              </div>
            </div>

            {!live && (
              <Note tone="warning" className="mt-4">
                Running in fallback mode — Razorpay Route did not accept this account yet. Until it does, orders settle to the platform and are paid out manually.
              </Note>
            )}
            {live && !settlementReady && (
              <Note tone="info" className="mt-4">
                Razorpay is verifying your bank account. This usually takes a few minutes to a couple of hours. Use “Refresh status” to check.
              </Note>
            )}

            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <Btn variant="ghost" data-testid="route-refresh-btn" onClick={refresh} disabled={refreshing}>
                {refreshing ? "Checking…" : "Refresh status"}
              </Btn>
              <Btn variant="danger" data-testid="route-disconnect-btn" onClick={disconnect}>
                Disconnect Account
              </Btn>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xs">
            <h4 className="font-bold text-[#0A0A0A] text-sm mb-4">Enter Bank Account Details</h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Legal / Registered Name"
                data-testid="route-legal"
                placeholder="e.g. Studio Craft Enterprises"
                value={form.legal_business_name}
                onChange={upd("legal_business_name")}
              />
              <Field
                label="Primary Contact Name"
                data-testid="route-contact"
                placeholder="e.g. Aisha Sharma"
                value={form.contact_name}
                onChange={upd("contact_name")}
              />
              <Field
                label="Phone Number"
                data-testid="route-phone"
                placeholder="9876543210"
                value={form.phone}
                onChange={upd("phone")}
              />
              <Field
                label="Beneficiary / Account Holder Name"
                data-testid="route-beneficiary"
                placeholder="Name as printed on the bank passbook"
                value={form.beneficiary_name}
                onChange={upd("beneficiary_name")}
              />
              <Field
                label="Bank Account Number"
                data-testid="route-account"
                placeholder="Digits only"
                inputMode="numeric"
                value={form.account_number}
                onChange={upd("account_number")}
              />
              <Field
                label="Bank IFSC Code"
                data-testid="route-ifsc"
                placeholder="e.g. HDFC0001234"
                value={form.ifsc}
                onChange={upd("ifsc")}
                helper="11 characters — 4 letters, a 0, then 6 digits/letters."
              />
            </div>
            <div className="mt-6 flex justify-end">
              <Btn variant="primary" data-testid="route-connect-btn" onClick={connect} disabled={busy}>
                {busy ? "Verifying & Connecting..." : "Connect Bank Payouts"}
              </Btn>
            </div>
          </div>
        )}

        {msg && <Note tone={msgTone}>{msg}</Note>}
      </div>
    </Panel>
  );
}

/* ==========================================================================
   PRODUCTS & CATALOG SECTION
   ========================================================================== */
function ProductsSection({
  hasStore,
  viewMode = "grid",
  setViewMode,
  showAddModal,
  setShowAddModal,
  products = [],
  productsError = "",
  loadProducts,
}) {
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [stockFilter, setStockFilter] = useState("all"); // 'all' | 'in_stock' | 'low_stock' | 'sold_out'

  const productList = Array.isArray(products) ? products : [];

  // External "Add Product" trigger (hero button / quick-add card)
  useEffect(() => {
    if (showAddModal) {
      setEditingProduct(null);
      setEditorOpen(true);
    }
  }, [showAddModal]);

  const openCreate = () => {
    setEditingProduct(null);
    setEditorOpen(true);
  };
  const openEdit = (p) => {
    setEditingProduct(p);
    setEditorOpen(true);
  };
  const closeEditor = () => {
    setEditorOpen(false);
    setEditingProduct(null);
    setShowAddModal && setShowAddModal(false);
  };

  // Filter products by search and stock
  const filteredProducts = useMemo(() => {
    return productList.filter((p) => {
      const matchesSearch =
        !searchQuery ||
        p.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.description?.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (stockFilter === "in_stock") return p.stock === null || p.stock > 5;
      if (stockFilter === "low_stock") return p.stock !== null && p.stock > 0 && p.stock <= 5;
      if (stockFilter === "sold_out") return p.stock === 0;

      return true;
    });
  }, [productList, searchQuery, stockFilter]);

  const del = async (id) => {
    if (confirm("Delete this product from your store?")) {
      await api.delete(`/products/${id}`);
      loadProducts();
    }
  };

  if (!hasStore) {
    return (
      <Panel title="Products" testId="products-panel">
        <p className="text-sm text-neutral-500">Create a store first.</p>
      </Panel>
    );
  }

  return (
    <div className="space-y-6">
      <ProductEditor
        open={editorOpen}
        product={editingProduct}
        onClose={closeEditor}
        onSaved={loadProducts}
      />

      {/* Catalog Search & Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-neutral-200/90 bg-white p-4 shadow-sm">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search products by title or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-neutral-200 bg-neutral-50/50 pl-9 pr-4 py-2 text-xs sm:text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:bg-white"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 text-xs"
            >
              Clear
            </button>
          )}
        </div>

        {/* Filters & View Switcher */}
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          {/* Stock Filter Pills */}
          <div className="flex rounded-xl border border-neutral-200 bg-neutral-50 p-1 text-xs font-bold">
            <button
              onClick={() => setStockFilter("all")}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                stockFilter === "all" ? "bg-white text-neutral-900 shadow-2xs" : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              All ({productList.length})
            </button>
            <button
              onClick={() => setStockFilter("low_stock")}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                stockFilter === "low_stock" ? "bg-white text-amber-700 shadow-2xs" : "text-neutral-500 hover:text-amber-700"
              }`}
            >
              Low Stock
            </button>
            <button
              onClick={() => setStockFilter("sold_out")}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                stockFilter === "sold_out" ? "bg-white text-rose-700 shadow-2xs" : "text-neutral-500 hover:text-rose-700"
              }`}
            >
              Sold Out
            </button>
          </div>

          {/* Grid / Table Toggle */}
          <div className="flex rounded-xl border border-neutral-200 bg-neutral-50 p-1">
            <button
              onClick={() => setViewMode && setViewMode("grid")}
              className={`rounded-lg p-1.5 transition-all ${
                viewMode === "grid" ? "bg-white text-neutral-900 shadow-2xs" : "text-neutral-400 hover:text-neutral-700"
              }`}
              title="Grid View"
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode && setViewMode("table")}
              className={`rounded-lg p-1.5 transition-all ${
                viewMode === "table" ? "bg-white text-neutral-900 shadow-2xs" : "text-neutral-400 hover:text-neutral-700"
              }`}
              title="Table View"
            >
              <List className="h-4 w-4" />
            </button>
          </div>

          {/* Add Product Button */}
          <Btn
            variant="primary"
            data-testid="open-add-product-btn"
            onClick={openCreate}
            className="py-2"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Add Product</span>
          </Btn>
        </div>
      </div>

      {/* Grid View */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {/* Quick Add Card */}
          <button
            type="button"
            onClick={openCreate}
            className="group flex aspect-square flex-col items-center justify-center rounded-2xl border-2 border-dashed border-neutral-200 bg-neutral-50/50 p-6 text-center transition-all hover:border-[#FF4F00] hover:bg-[#FFF4E0]/20"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white border border-neutral-200 shadow-2xs transition-transform group-hover:scale-110 group-hover:bg-[#FF4F00] group-hover:text-white group-hover:border-[#FF4F00]">
              <Plus className="h-6 w-6" />
            </div>
            <span className="mt-3 text-xs font-bold text-neutral-900">Add New Item</span>
            <span className="mt-0.5 text-[11px] text-neutral-400">Post product to shop</span>
          </button>

          {/* Product Cards */}
          {filteredProducts.map((p) => {
            const photos = (p.images && p.images.length) ? p.images.length : (p.image ? 1 : 0);
            return (
            <div
              key={p.product_id}
              data-testid={`product-card-${p.product_id}`}
              onClick={() => openEdit(p)}
              className="group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs transition-all hover:shadow-md hover:border-neutral-300"
            >
              {/* Product Image Container */}
              <div className="relative aspect-square w-full overflow-hidden bg-neutral-100">
                {p.image ? (
                  <img
                    src={fileUrl(p.image)}
                    alt={p.title}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="flex h-full w-full flex-col items-center justify-center bg-neutral-100 p-4 text-center">
                    <Package className="h-10 w-10 text-neutral-300" />
                    <span className="mt-2 text-xs font-bold text-neutral-500 line-clamp-1">{p.title}</span>
                  </div>
                )}

                {!p.active && (
                  <span className="absolute left-2.5 top-2.5 rounded-full bg-neutral-900/80 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                    Hidden
                  </span>
                )}
                {photos > 1 && (
                  <span className="absolute bottom-2.5 left-2.5 rounded-full bg-neutral-900/70 px-2 py-0.5 text-[10px] font-bold text-white">
                    {photos} photos
                  </span>
                )}

                {/* Stock Status Badge */}
                <div className="absolute top-2.5 right-2.5">
                  {p.stock === 0 ? (
                    <span className="rounded-full bg-rose-500 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                      Sold Out
                    </span>
                  ) : p.stock !== null && p.stock <= 5 ? (
                    <span className="rounded-full bg-amber-500 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                      Only {p.stock} left
                    </span>
                  ) : p.stock !== null ? (
                    <span className="rounded-full bg-neutral-900/80 backdrop-blur-xs px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
                      {p.stock} in stock
                    </span>
                  ) : null}
                </div>

                {/* Hover actions */}
                <div className="absolute bottom-2.5 right-2.5 flex gap-1.5 opacity-0 transition-all group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); openEdit(p); }}
                    className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/95 text-neutral-700 shadow-sm hover:bg-neutral-900 hover:text-white"
                    title="Edit product"
                    data-testid={`product-edit-${p.product_id}`}
                  >
                    <Edit3 className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); del(p.product_id); }}
                    className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/95 text-neutral-600 shadow-sm hover:bg-rose-600 hover:text-white"
                    title="Delete product"
                    data-testid={`product-del-${p.product_id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Product Info */}
              <div className="p-3.5">
                <h4 className="text-xs sm:text-sm font-bold text-[#0A0A0A] line-clamp-1">{p.title}</h4>
                {p.description && (
                  <p className="mt-0.5 text-xs text-neutral-400 line-clamp-1">{p.description}</p>
                )}
                <div className="mt-2 flex items-center justify-between border-t border-neutral-100 pt-2">
                  <span className="font-black text-sm text-[#0A0A0A]">₹{p.price}</span>
                  {(p.optionGroups || []).length > 0 && (
                    <span className="text-[10px] font-bold text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full">
                      {p.optionGroups.length} variant{p.optionGroups.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </div>
            </div>
            );
          })}
        </div>
      )}

      {/* Table View */}
      {viewMode === "table" && (
        <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs">
          <div className="overflow-x-auto">
            <table data-testid="products-table" className="w-full min-w-[600px] text-left text-sm">
              <thead className="border-b border-neutral-100 bg-neutral-50/60 text-xs font-bold uppercase tracking-wider text-neutral-500">
                <tr>
                  <th className="px-5 py-3.5">Product</th>
                  <th className="px-5 py-3.5">Price</th>
                  <th className="px-5 py-3.5">Stock</th>
                  <th className="px-5 py-3.5">Variants</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {filteredProducts.map((p) => (
                  <tr
                    key={p.product_id}
                    data-testid={`product-row-${p.product_id}`}
                    className="hover:bg-neutral-50/60 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="h-11 w-11 shrink-0 overflow-hidden rounded-xl border border-neutral-100 bg-neutral-50">
                          {p.image ? (
                            <img src={fileUrl(p.image)} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center text-xs text-neutral-400">
                              <Package className="h-5 w-5" />
                            </div>
                          )}
                        </div>
                        <div>
                          <span className="font-bold text-[#0A0A0A] block">{p.title}</span>
                          {p.description && (
                            <p className="text-xs text-neutral-400 line-clamp-1 max-w-xs">{p.description}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 font-bold text-[#0A0A0A]">₹{p.price}</td>
                    <td className="px-5 py-3.5 text-xs">
                      {p.stock === 0 ? (
                        <span className="font-bold text-rose-600">Sold out</span>
                      ) : p.stock !== null ? (
                        <span className="font-medium text-neutral-700">{p.stock} units</span>
                      ) : (
                        <span className="text-neutral-400 font-medium">Unlimited</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-neutral-500">
                      {(p.optionGroups || []).map((g) => `${g?.name || "Option"}`).join(", ") || "None"}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-1">
                        <button
                          data-testid={`product-edit-row-${p.product_id}`}
                          onClick={() => openEdit(p)}
                          className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-800 transition-colors"
                          title="Edit product"
                        >
                          <Edit3 className="h-4 w-4" />
                        </button>
                        <button
                          data-testid={`product-del-row-${p.product_id}`}
                          onClick={() => del(p.product_id)}
                          className="rounded-lg p-1.5 text-neutral-400 hover:bg-rose-50 hover:text-rose-600 transition-colors"
                          title="Delete product"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {filteredProducts.length === 0 && productsError && (
        <div
          data-testid="products-load-error"
          className="rounded-2xl border border-dashed border-rose-200 bg-rose-50/40 p-12 text-center"
        >
          <AlertTriangle className="mx-auto h-10 w-10 text-rose-300" />
          <h4 className="mt-3 text-sm font-bold text-[#0A0A0A]">Couldn't load your products</h4>
          <p className="mt-1 text-xs text-neutral-600">{productsError}</p>
          <p className="mt-1 text-xs text-neutral-500">
            Your listings are safe — this is a connection problem, not an empty shop.
          </p>
          <Btn variant="outline" className="mt-4" onClick={loadProducts}>
            Try again
          </Btn>
        </div>
      )}

      {filteredProducts.length === 0 && !productsError && (
        <div className="rounded-2xl border border-dashed border-neutral-200 p-12 text-center">
          <Package className="mx-auto h-10 w-10 text-neutral-300" />
          <h4 className="mt-3 font-bold text-[#0A0A0A] text-sm">No products found</h4>
          <p className="mt-1 text-xs text-neutral-500">
            {searchQuery ? "Try adjusting your search query." : "List your first item to start making sales."}
          </p>
        </div>
      )}
    </div>
  );
}

/* ==========================================================================
   ORDER FULFILLMENT & PIPELINE SECTION
   ========================================================================== */
function OrdersSection({ onChanged }) {
  const [data, setData] = useState({ orders: [], total: 0, page: 1, pages: 1 });
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("all");
  const limit = 20;

  const load = useCallback(async () => {
    try {
      const q = statusFilter !== "all" ? `&status=${statusFilter}` : "";
      const { data: d } = await api.get(`/orders?page=${page}&limit=${limit}${q}`);
      setData(d || { orders: [], total: 0, page: 1, pages: 1 });
    } catch {
      setData({ orders: [], total: 0, page: 1, pages: 1 });
    }
  }, [page, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const orders = data.orders || [];
  const readyToShip = orders.filter((o) => o.status === "paid");

  const [shipping, setShipping] = useState(false);
  const [shipMsg, setShipMsg] = useState(null);

  /** Dispatch every paid order on this page in one request. Each still goes
   *  through the normal ship path server-side, so delivery codes are generated
   *  and emailed exactly as they are for a single order. */
  const shipAll = async () => {
    if (!readyToShip.length) return;
    setShipping(true);
    setShipMsg(null);
    try {
      const { data: res } = await api.post("/orders/bulk-ship", {
        orderIds: readyToShip.map((o) => o.order_id),
      });
      const n = res.shipped?.length || 0;
      setShipMsg({
        tone: res.failed?.length ? "warning" : "success",
        text: res.failed?.length
          ? `Dispatched ${n}. ${res.failed.length} could not be shipped — open them individually.`
          : `Dispatched ${n} order${n === 1 ? "" : "s"}. Delivery codes have gone out to the buyers.`,
      });
      await load();
      onChanged?.();
    } catch (e) {
      setShipMsg({ tone: "error", text: formatApiError(e.response?.data?.detail) });
    } finally {
      setShipping(false);
    }
  };

  return (
    <Panel
      title="Orders & Customer Fulfillment"
      subtitle="Track customer orders, delivery OTP verification, and payouts in real time."
      testId="orders-panel"
      action={
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-700">
            {data.total} Total Orders
          </span>
        </div>
      }
    >
      <div className="space-y-5">
        {readyToShip.length > 0 && (
          <div
            data-testid="bulk-ship-bar"
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-[#0A0A0A] px-4 py-3"
          >
            <div className="min-w-0">
              <p className="text-[13px] font-bold text-white">
                {readyToShip.length} order{readyToShip.length > 1 ? "s are" : " is"} paid and ready to pack
              </p>
              <p className="text-xs font-medium text-neutral-400">
                Dispatching sends each buyer their delivery code.
              </p>
            </div>
            <button
              type="button"
              onClick={shipAll}
              disabled={shipping}
              data-testid="bulk-ship-btn"
              className="shrink-0 rounded-lg bg-[#FF4F00] px-3.5 py-2 text-xs font-extrabold text-white transition-colors hover:bg-[#E04500] disabled:opacity-60"
            >
              {shipping ? "Dispatching…" : `Mark ${readyToShip.length} as shipped`}
            </button>
          </div>
        )}

        {shipMsg && <Note tone={shipMsg.tone}>{shipMsg.text}</Note>}

        {/* Status Filter Tabs */}
        <div className="flex gap-1.5 overflow-x-auto pb-1 text-xs font-bold scrollbar-none">
          {[
            { id: "all", label: "All Orders" },
            { id: "placed", label: "Unpaid" },
            { id: "paid", label: "Ready to Ship" },
            { id: "shipped", label: "In Transit" },
            { id: "delivered", label: "Delivered" },
            { id: "completed", label: "Completed" },
            { id: "disputed", label: "Disputed" },
            // Checkouts nobody paid for. Kept out of the default list because
            // they need nothing doing, but a seller wondering where their
            // stock went should be able to find them.
            { id: "abandoned", label: "Not paid" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`rounded-xl px-3 py-1.5 transition-all whitespace-nowrap ${
                statusFilter === tab.id
                  ? "bg-neutral-900 text-white shadow-2xs"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200/70"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Desktop Table View */}
        <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs">
          <div className="overflow-x-auto">
            <table data-testid="orders-table" className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-neutral-100 bg-neutral-50/60 text-xs font-bold uppercase tracking-wider text-neutral-500">
                <tr>
                  <th className="px-5 py-3.5">Order ID</th>
                  <th className="px-5 py-3.5">Buyer</th>
                  <th className="px-5 py-3.5">Items</th>
                  <th className="px-5 py-3.5">Amount</th>
                  <th className="px-5 py-3.5">Fulfillment Status</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {orders.map((o) => (
                  <tr
                    key={o.order_id}
                    data-testid={`order-row-${o.order_id}`}
                    className="hover:bg-neutral-50/60 transition-colors"
                  >
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-neutral-800">
                      #{o.order_id}
                    </td>
                    <td className="px-5 py-3.5">
                      <div>
                        <span className="font-bold text-[#0A0A0A] block">{o.buyerName}</span>
                        <span className="text-xs text-neutral-400">{o.buyerEmail}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-neutral-600">
                      {(o.items || []).length} item{(o.items || []).length > 1 ? "s" : ""}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="font-bold text-[#0A0A0A]">₹{o.amount}</span>
                      {o.paymentMethod === "cod" && (
                        <span className="ml-2 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                          COD
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusPill status={o.status} data-testid={`order-status-${o.order_id}`} />
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        to={`/orders/${o.order_id}`}
                        data-testid={`order-open-desktop-${o.order_id}`}
                        className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-800 shadow-2xs hover:bg-neutral-50 hover:border-neutral-300 transition-all"
                      >
                        Manage →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {orders.length === 0 && (
          <div className="rounded-2xl border border-dashed border-neutral-200 p-12 text-center">
            <ShoppingBag className="mx-auto h-10 w-10 text-neutral-300" />
            <h4 className="mt-3 font-bold text-[#0A0A0A] text-sm">No orders found</h4>
            <p className="mt-1 text-xs text-neutral-500">
              {statusFilter !== "all"
                ? `No orders matching status "${statusFilter.replace(/_/g, " ")}".`
                : "Customer orders will appear here once placed on your storefront."}
            </p>
          </div>
        )}

        {/* Pagination */}
        {data.total > limit && (
          <div className="flex items-center justify-between border-t border-neutral-100 pt-4" data-testid="orders-pagination">
            <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">
              Page {data.page} of {data.pages}
            </span>
            <div className="flex items-center gap-2">
              <button
                data-testid="orders-prev"
                disabled={data.page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-xl border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-700 transition-all hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                data-testid="orders-next"
                disabled={data.page >= data.pages}
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                className="rounded-xl border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-700 transition-all hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}

/* ==========================================================================
   PLAN & BILLING SECTION
   ========================================================================== */
const fmtDate = (v) => {
  if (!v) return null;
  try {
    return new Date(v).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return null;
  }
};

function SubscriptionSection({ onChange }) {
  const { user, checkAuth } = useAuth();
  const [sub, setSub] = useState(null);
  const [subscribing, setSubscribing] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/subscription");
      setSub(data);
    } catch {}
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadScript = () =>
    new Promise((res) => {
      if (window.Razorpay) return res(true);
      const s = document.createElement("script");
      s.src = "https://checkout.razorpay.com/v1/checkout.js";
      s.onload = () => res(true);
      s.onerror = () => res(false);
      document.body.appendChild(s);
    });

  const subscribe = async (interval) => {
    setErrorMsg("");
    setSuccessMsg("");
    setSubscribing(interval);
    try {
      const { data } = await api.post("/subscription/create", { interval });
      const ok = await loadScript();
      if (!ok || !window.Razorpay) {
        setErrorMsg("Could not load the payment window. Check your connection and try again.");
        setSubscribing(null);
        return;
      }

      const rzp = new window.Razorpay({
        key: data.keyId,
        order_id: data.orderId,
        amount: data.amount * 100,
        currency: data.currency || "INR",
        name: "Stall Wise",
        description: `${data.tier} · ${interval}`,
        prefill: { email: user?.email || "", name: user?.name || "" },
        theme: { color: "#FF4F00" },
        modal: { ondismiss: () => setSubscribing(null) },
        handler: async (res) => {
          try {
            await api.post("/subscription/verify-payment", {
              razorpay_order_id: res.razorpay_order_id,
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_signature: res.razorpay_signature,
            });
            setSuccessMsg(`Stall Wise Pro (${interval}) is now active.`);
            await load();
            await checkAuth?.();
            onChange?.();
          } catch (e) {
            setErrorMsg(formatApiError(e.response?.data?.detail) || "Payment verification failed.");
          } finally {
            setSubscribing(null);
          }
        },
      });
      rzp.on("payment.failed", (response) => {
        setErrorMsg(response.error?.description || "Payment failed. Please try again.");
        setSubscribing(null);
      });
      rzp.open();
    } catch (e) {
      setErrorMsg(formatApiError(e.response?.data?.detail) || "Could not start checkout. Please try again.");
      setSubscribing(null);
    }
  };

  const active = (sub?.subscriptionStatus || user?.subscriptionStatus) === "active";
  const monthly = sub?.plans?.monthly ?? 199;
  const yearly = sub?.plans?.yearly ?? 1499;
  const commissionPct = Math.round(((sub?.commissionRate ?? 0.1) * 100));
  const renews = fmtDate(sub?.subscriptionExpiresAt);
  const busy = Boolean(subscribing);

  return (
    <Panel
      title="Plan & Billing"
      subtitle="Free Plan takes a commission on each sale. Stall Wise Pro removes storefront ads."
      testId="subscription-panel"
      action={
        <span
          data-testid="sub-status"
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${
            active ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-neutral-100 text-neutral-600 border-neutral-200"
          }`}
        >
          {active ? <><Sparkles className="h-3.5 w-3.5" /> Pro</> : "Free Plan"}
        </span>
      }
    >
      <div className="space-y-6">
        {/* Current plan summary */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-neutral-200 bg-neutral-50/60 p-4">
          <div>
            <p className="text-sm font-bold text-[#0A0A0A]">
              {active ? "Stall Wise Pro" : "Free Plan"}
              {active && sub?.subscriptionInterval ? ` · ${sub.subscriptionInterval}` : ""}
            </p>
            <p className="mt-0.5 text-xs text-neutral-500">
              {active
                ? renews ? `Renews ${renews}` : "Active"
                : `${commissionPct}% platform commission on each completed sale`}
            </p>
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          {/* Monthly */}
          <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xs transition-all hover:border-neutral-300">
            <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">Monthly</span>
            <p className="mt-3 text-3xl font-black text-[#0A0A0A]">
              ₹{monthly}<span className="text-xs font-medium text-neutral-500"> / month</span>
            </p>
            <ul className="mt-4 space-y-2 text-xs text-neutral-600">
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-600" /> Ad-free storefront</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-600" /> Direct bank settlements</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-emerald-600" /> Pro seller badge</li>
            </ul>
            <Btn
              variant="outline"
              data-testid="sub-monthly-btn"
              disabled={busy || (active && sub?.subscriptionInterval === "monthly")}
              onClick={() => subscribe("monthly")}
              className="mt-6 w-full"
            >
              {subscribing === "monthly" ? "Opening checkout…" : active && sub?.subscriptionInterval === "monthly" ? "Current plan" : `Choose Monthly · ₹${monthly}`}
            </Btn>
          </div>

          {/* Yearly */}
          <div className="relative overflow-hidden rounded-2xl border-2 border-neutral-900 bg-neutral-900 p-6 text-white shadow-md">
            <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[#FF4F00]/20 blur-2xl pointer-events-none" />
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">Annual</span>
              <span className="rounded-full bg-[#FF4F00] px-2.5 py-0.5 text-[10px] font-bold text-white">
                Save ₹{Math.max(0, monthly * 12 - yearly)}
              </span>
            </div>
            <p className="mt-3 text-3xl font-black text-white">
              ₹{yearly}<span className="text-xs font-medium text-neutral-400"> / year</span>
            </p>
            <ul className="mt-4 space-y-2 text-xs text-neutral-300">
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Everything in Monthly</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Two months free vs monthly</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Priority dispute resolution</li>
            </ul>
            <Btn
              variant="primary"
              data-testid="sub-yearly-btn"
              disabled={busy || (active && sub?.subscriptionInterval === "yearly")}
              onClick={() => subscribe("yearly")}
              className="mt-6 w-full"
            >
              {subscribing === "yearly" ? "Opening checkout…" : active && sub?.subscriptionInterval === "yearly" ? "Current plan" : `Choose Annual · ₹${yearly}`}
            </Btn>
          </div>
        </div>

        {errorMsg && <Note tone="error">{errorMsg}</Note>}
        {successMsg && <Note tone="success">{successMsg}</Note>}
      </div>
    </Panel>
  );
}

/* ==========================================================================
   MAIN EXECUTIVE DASHBOARD
   ========================================================================== */
export default function Dashboard() {
  const { user, logout, refreshUser } = useAuth();
  const [store, setStore] = useState(() => {
    try {
      const raw = localStorage.getItem("stallwise_store");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [storeLoaded, setStoreLoaded] = useState(() => {
    try { return Boolean(localStorage.getItem("stallwise_store")); } catch { return false; }
  });
  const [products, setProducts] = useState([]);
  const [productsError, setProductsError] = useState("");
  const [orders, setOrders] = useState([]);
  const [orderCount, setOrderCount] = useState(0);
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const [activeTab, setActiveTab] = useState("home");
  const [viewMode, setViewMode] = useState("grid");
  const [showAddModal, setShowAddModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  useDocumentMeta({
    title: "Seller console | Stall Wise",
    description: "Manage your storefront, orders, payouts and settings on Stall Wise.",
    path: "/dashboard",
  });

  const loadProducts = useCallback(async () => {
    try {
      const { data } = await api.get("/products");
      if (Array.isArray(data)) setProducts(data);
      else if (data?.products) setProducts(data.products);
      else setProducts([]);
      setProductsError("");
    } catch (e) {
      // Don't collapse a failed request into an empty catalogue — "you have no
      // products" and "we couldn't reach the server" look identical to a seller
      // and send them hunting for a bug in the wrong place.
      setProducts([]);
      setProductsError(
        formatApiError(e.response?.data?.detail) ||
          "Couldn't load your products. Check your connection and try again."
      );
    }
  }, []);

  const loadStore = useCallback(async (updated) => {
    if (updated) {
      setStore(updated);
      try { localStorage.setItem("stallwise_store", JSON.stringify(updated)); } catch {}
      setStoreLoaded(true);
      return;
    }
    try {
      const { data } = await api.get("/stores/me");
      if (data) {
        setStore(data);
        try { localStorage.setItem("stallwise_store", JSON.stringify(data)); } catch {}
      } else {
        setStore(null);
        try { localStorage.removeItem("stallwise_store"); } catch {}
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setStore(null);
        try { localStorage.removeItem("stallwise_store"); } catch {}
      }
    } finally {
      setStoreLoaded(true);
    }
  }, []);

  const loadOrders = useCallback(async () => {
    try {
      const { data: d } = await api.get("/orders?limit=100");
      setOrders(d?.orders || []);
      setOrderCount(d?.total || 0);
    } catch {
      setOrders([]);
    }
  }, []);

  /** Every figure on Home, Insights and Payouts comes from here — one request,
   *  computed server-side against all of the seller's rows rather than the
   *  first page of orders. */
  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const { data } = await api.get("/dashboard/summary");
      setSummary(data);
      setSummaryError("");
    } catch (e) {
      setSummary(null);
      setSummaryError(formatApiError(e.response?.data?.detail) || "");
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const refreshAll = useCallback(() => {
    loadProducts();
    loadOrders();
    loadSummary();
  }, [loadProducts, loadOrders, loadSummary]);

  useEffect(() => {
    loadStore();
    loadProducts();
    loadOrders();
    loadSummary();
  }, [loadStore, loadProducts, loadOrders, loadSummary]);

  useEffect(() => {
    if (storeLoaded && store === null && user && !user?.hasStore) {
      navigate("/onboarding", { replace: true });
    }
  }, [storeLoaded, store, user, navigate]);

  const counts = useMemo(() => ({
    toShip: summary?.queue?.toShip ?? 0,
    products: products.length,
    bankReady: summary?.queue?.bankReady,
    isPro: summary?.metrics?.isPro ?? (user?.subscriptionStatus === "active"),
    commissionRate: summary?.metrics?.commissionRate ?? 0.1,
    commissionThisMonth: summary?.metrics?.commissionThisMonth ?? 0,
    needsAttention:
      (summary?.queue?.toShip ?? 0) +
      (summary?.queue?.awaitingOtp ?? 0) +
      (summary?.queue?.disputed ?? 0),
    copied,
    onCopied: () => { setCopied(true); setTimeout(() => setCopied(false), 2500); },
  }), [summary, products.length, user?.subscriptionStatus, copied]);

  const onLogout = async () => { await logout(); navigate("/login"); };

  const HEADINGS = {
    home: ["Home", store?.name ? `${store.name} · ${new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}` : ""],
    orders: ["Orders", counts.toShip ? `${counts.toShip} paid order${counts.toShip > 1 ? "s" : ""} waiting to be packed` : "Everything is fulfilled"],
    products: ["Products", `${products.length} listing${products.length === 1 ? "" : "s"}`],
    customers: ["Customers", "People who have bought from you"],
    insights: ["Insights", "What is selling, and to whom"],
    payouts: ["Payouts", "Where your money is right now"],
    settings: ["Settings", "Shop details, delivery, tax and alerts"],
  };
  const [title, subtitle] = HEADINGS[activeTab] || HEADINGS.home;

  const addProductBtn = (activeTab === "products" || activeTab === "home") && store ? (
    <Btn variant="primary" className="h-9 !py-0" onClick={() => { setShowAddModal(true); setActiveTab("products"); }}>
      <Plus className="h-4 w-4" /> Add product
    </Btn>
  ) : null;

  return (
    <Shell
      store={store}
      user={user}
      active={activeTab}
      onNav={setActiveTab}
      counts={counts}
      onLogout={onLogout}
      title={title}
      subtitle={subtitle}
      action={addProductBtn}
    >
      {activeTab === "home" && (
        <HomeSection summary={summary} loading={summaryLoading} error={summaryError} onRetry={loadSummary} orders={orders} onNav={setActiveTab} store={store} />
      )}

      {activeTab === "products" && (
        <ProductsSection
          hasStore={!!store}
          viewMode={viewMode}
          setViewMode={setViewMode}
          showAddModal={showAddModal}
          setShowAddModal={setShowAddModal}
          products={products}
          productsError={productsError}
          loadProducts={refreshAll}
        />
      )}

      {activeTab === "orders" && <OrdersSection onChanged={refreshAll} />}

      {activeTab === "customers" && <CustomersSection summary={summary} orders={orders} loading={summaryLoading} />}

      {activeTab === "insights" && <InsightsSection summary={summary} loading={summaryLoading} />}

      {activeTab === "payouts" && (
        <MoneySection summary={summary} loading={summaryLoading}>
          <div className="flex flex-col gap-5">
            <RouteSection onChange={refreshAll} />
            <SubscriptionSection onChange={() => { refreshUser?.(); refreshAll(); }} />
          </div>
        </MoneySection>
      )}

      {activeTab === "settings" && (
        <div className="flex flex-col gap-5">
          <StoreSection store={store} onChange={loadStore} user={user} refreshUser={refreshUser} />
          <ShopSettings store={store} onSaved={loadStore} />
          <AccountSection user={user} onLogout={onLogout} />
        </div>
      )}

      {/* Applying a proposal writes to the same tables the console reads, so a
          successful apply pulls the whole console fresh rather than leaving a
          panel showing the old price. */}
      {store && (
        <Assistant onApplied={() => { refreshAll(); loadStore(); }} />
      )}
    </Shell>
  );
}

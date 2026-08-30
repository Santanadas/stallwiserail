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
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Panel, Field, Btn, StatusPill, Note } from "@/components/Kit";
import ImageUpload, { fileUrl } from "@/components/ImageUpload";
import StoreQrModal from "@/components/StoreQrModal";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

/* ==========================================================================
   STORE SETTINGS SECTION
   ========================================================================== */
function StoreSection({ store, onChange, user, refreshUser }) {
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!store) return null;

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

  return (
    <Panel
      title="Store Identity & Preferences"
      subtitle="Configure how your shop appears to buyers across Stall Wise."
      testId="store-panel"
      action={
        store?.slug ? (
          <Link
            to={`/${store.slug}`}
            target="_blank"
            data-testid="store-shop-link"
            className="inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-bold text-neutral-800 transition-all hover:bg-neutral-100 hover:border-neutral-300"
          >
            <span>Preview Storefront</span>
            <ExternalLink className="h-3.5 w-3.5 text-neutral-500" />
          </Link>
        ) : null
      }
    >
      <div className="space-y-6">
        {/* Profile Photo Upload */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-5 rounded-2xl border border-neutral-100 bg-neutral-50/50 p-5">
          <div className="relative shrink-0">
            <ImageUpload
              value={user?.avatar}
              onChange={setAvatar}
              kind="avatar"
              shape="round"
              label="Upload logo"
              testId="store-avatar"
            />
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#0A0A0A]">Store Brand & Logo</h4>
            <p className="mt-1 text-xs text-neutral-500 max-w-md">
              Square image recommended (300×300px). This will appear on your shop banner, customer receipts, and product cards.
            </p>
          </div>
        </div>

        {/* Inputs */}
        <div className="grid gap-5 sm:grid-cols-2">
          <Field
            label="Store Name"
            data-testid="store-name-edit"
            value={store?.name || ""}
            placeholder="e.g. Studio Craft Ceramics"
            onChange={(e) => onChange({ ...store, name: e.target.value }, true)}
            helper="Your public brand name"
          />
          <Field
            label="Delivery Acceptance Window (Minutes)"
            data-testid="store-window-edit"
            type="number"
            value={store?.acceptanceWindowMinutes ?? 120}
            onChange={(e) => onChange({ ...store, acceptanceWindowMinutes: e.target.value }, true)}
            helper="Time allocated for delivery confirmation after shipping (Default: 120 min)"
          />
        </div>

        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-neutral-600 mb-1.5 block">
            Store Bio / Description
          </span>
          <textarea
            data-testid="store-bio-edit"
            rows={3}
            placeholder="Tell buyers what makes your products special, packaging details, or shipping policies..."
            value={store?.bio || ""}
            onChange={(e) => onChange({ ...store, bio: e.target.value }, true)}
            className="w-full rounded-xl border border-neutral-200 bg-white p-3.5 text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10"
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Btn variant="primary" data-testid="store-save-btn" onClick={save} disabled={busy}>
            {busy ? "Saving..." : "Save Store Changes"}
          </Btn>
          {saved && (
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-bold text-emerald-700"
            >
              <Check className="h-3.5 w-3.5" /> Changes saved successfully!
            </motion.span>
          )}
        </div>

        {err && <Note tone="error">{err}</Note>}
      </div>
    </Panel>
  );
}

/* ==========================================================================
   PAYMENT ROUTE & SETTLEMENT SECTION
   ========================================================================== */
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
  const [busy, setBusy] = useState(false);
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/seller/route");
      setRoute(data);
    } catch {}
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connect = async () => {
    setMsg("");
    setBusy(true);
    try {
      await api.post("/seller/route/onboard", form);
      setMsg("Bank payout account connected successfully! Customer payments settle directly to your account.");
      setForm({
        legal_business_name: "",
        contact_name: "",
        phone: "",
        beneficiary_name: "",
        account_number: "",
        ifsc: "",
      });
      load();
      onChange();
    } catch (e) {
      setMsg(formatApiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    if (confirm("Disconnect direct bank payouts?")) {
      await api.delete("/seller/route");
      load();
      onChange();
    }
  };

  return (
    <Panel
      title="Direct Bank Settlement & Razorpay Route"
      subtitle="Customer payments settle automatically to your verified bank account."
      testId="route-panel"
      action={
        <span
          data-testid="route-status"
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${
            route?.connected
              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
              : "bg-neutral-100 border-neutral-200 text-neutral-600"
          }`}
        >
          {route?.connected ? (
            <>
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Settlement Active</span>
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
              Stall Wise is powered by Razorpay Route. When a customer purchases from your store, payouts are settled directly into your linked bank account based on your store's active plan. No holding periods, no manual withdrawal requests.
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
                  <p className="mt-1 font-mono text-sm font-bold text-[#0A0A0A]">Ending in ••••{route.bankLast4}</p>
                </div>
              )}

              <div className="rounded-xl bg-white p-4 border border-neutral-100 shadow-2xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">Account Status</span>
                <p className="mt-1 font-bold text-emerald-600 capitalize text-sm">{route.status || "Verified"}</p>
              </div>
            </div>

            <div className="mt-5 flex justify-end">
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
                label="Legal / Registered Business Name"
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
                placeholder="Name as it appears on bank passbook"
                value={form.beneficiary_name}
                onChange={upd("beneficiary_name")}
              />
              <Field
                label="Bank Account Number"
                data-testid="route-account"
                placeholder="Enter account number"
                value={form.account_number}
                onChange={upd("account_number")}
              />
              <Field
                label="Bank IFSC Code"
                data-testid="route-ifsc"
                placeholder="e.g. HDFC0001234"
                value={form.ifsc}
                onChange={upd("ifsc")}
              />
            </div>
            <div className="mt-6 flex justify-end">
              <Btn variant="primary" data-testid="route-connect-btn" onClick={connect} disabled={busy}>
                {busy ? "Verifying & Connecting..." : "Connect Bank Payouts"}
              </Btn>
            </div>
          </div>
        )}

        {msg && (
          <Note tone={msg.toLowerCase().includes("connected") || msg.toLowerCase().includes("success") ? "success" : "error"}>
            {msg}
          </Note>
        )}
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
  loadProducts,
}) {
  const [form, setForm] = useState({ title: "", description: "", price: "", stock: "" });
  const [image, setImage] = useState(null);
  const [groups, setGroups] = useState([]);
  const [err, setErr] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [stockFilter, setStockFilter] = useState("all"); // 'all' | 'in_stock' | 'low_stock' | 'sold_out'

  const productList = Array.isArray(products) ? products : [];

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

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const addGroup = () => setGroups([...groups, { name: "", optionsText: "" }]);
  const updGroup = (i, k) => (e) => {
    const g = [...groups];
    g[i][k] = e.target.value;
    setGroups(g);
  };

  const parseGroups = () =>
    groups
      .filter((g) => g && g.name)
      .map((g) => ({
        name: g.name,
        options: (g.optionsText || "")
          .split(",")
          .map((line) => {
            const [label, priceDelta, stock] = line.split("|").map((x) => x.trim());
            return {
              label,
              priceDelta: Number(priceDelta || 0),
              stock: stock ? Number(stock) : null,
            };
          })
          .filter((o) => o.label),
      }));

  const create = async () => {
    setErr("");
    if (!form.title.trim()) {
      setErr("Please enter a product title");
      return;
    }
    if (!form.price || Number(form.price) <= 0) {
      setErr("Please enter a valid product price");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/products", {
        title: form.title,
        description: form.description,
        price: Number(form.price),
        stock: form.stock ? Number(form.stock) : null,
        optionGroups: parseGroups(),
        active: true,
        image,
      });
      setForm({ title: "", description: "", price: "", stock: "" });
      setImage(null);
      setGroups([]);
      if (setShowAddModal) setShowAddModal(false);
      loadProducts();
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

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
      {/* Product Creation Drawer / Modal */}
      <AnimatePresence>
        {showAddModal && (
          <motion.div
            initial={{ opacity: 0, y: -15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            className="overflow-hidden rounded-2xl border border-neutral-200 bg-white p-6 shadow-xl"
          >
            <div className="mb-6 flex items-center justify-between border-b border-neutral-100 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#FF4F00]/10 text-[#FF4F00]">
                  <Package className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-[#0A0A0A] text-base">Add New Product to Catalog</h3>
                  <p className="text-xs text-neutral-500">List items with custom sizes, colors and pricing</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-6">
              {/* Image Upload */}
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-neutral-600 mb-1.5 block">
                  Product Image
                </span>
                <ImageUpload
                  value={image}
                  onChange={setImage}
                  kind="product"
                  label="Upload item photo"
                  testId="product-image"
                />
              </div>

              {/* Basic Details */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Field
                  label="Title / Item Name"
                  data-testid="product-title"
                  placeholder="e.g. Handcrafted Ceramic Mug"
                  value={form.title}
                  onChange={upd("title")}
                />
                <Field
                  label="Price (₹ INR)"
                  data-testid="product-price"
                  type="number"
                  placeholder="599"
                  value={form.price}
                  onChange={upd("price")}
                />
                <Field
                  label="Inventory Stock (Units)"
                  data-testid="product-stock"
                  type="number"
                  placeholder="Leave empty for unlimited"
                  value={form.stock}
                  onChange={upd("stock")}
                />
                <Field
                  label="Short Caption / Tagline"
                  data-testid="product-desc"
                  placeholder="Materials, sizing & details"
                  value={form.description}
                  onChange={upd("description")}
                />
              </div>

              {/* Variant Groups */}
              <div className="rounded-xl border border-neutral-200/80 bg-neutral-50/50 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-neutral-700">
                      Product Options & Variants (Optional)
                    </span>
                    <p className="text-xs text-neutral-500">Add size, color, or material choices</p>
                  </div>
                  <Btn variant="ghost" data-testid="add-group-btn" onClick={addGroup} className="py-1.5 px-3 text-xs">
                    <Plus className="h-3.5 w-3.5" /> Add Option Group
                  </Btn>
                </div>

                {groups.map((g, i) => (
                  <div key={i} className="mt-3 grid gap-3 sm:grid-cols-3 items-end bg-white p-3 rounded-xl border border-neutral-200">
                    <Field
                      label={`Group ${i + 1} Name`}
                      data-testid={`group-name-${i}`}
                      placeholder="e.g. Size or Color"
                      value={g?.name || ""}
                      onChange={updGroup(i, "name")}
                    />
                    <div className="sm:col-span-2 flex items-end gap-2">
                      <div className="flex-1">
                        <Field
                          label="Options (label|priceDelta|stock)"
                          data-testid={`group-options-${i}`}
                          placeholder="Small|0|10, Large|150|5"
                          value={g?.optionsText || ""}
                          onChange={updGroup(i, "optionsText")}
                          helper="Format: Name | Extra ₹ | Quantity"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => setGroups(groups.filter((_, idx) => idx !== i))}
                        className="mb-1 rounded-lg p-2 text-rose-500 hover:bg-rose-50 transition-colors"
                        title="Remove group"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Form Action */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <Btn variant="outline" onClick={() => setShowAddModal(false)}>
                  Cancel
                </Btn>
                <Btn
                  variant="primary"
                  data-testid="product-create-btn"
                  onClick={create}
                  disabled={submitting}
                >
                  {submitting ? "Publishing..." : "Publish Product to Store"}
                </Btn>
              </div>

              {err && <Note tone="error">{err}</Note>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

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
            onClick={() => setShowAddModal && setShowAddModal(true)}
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
            onClick={() => setShowAddModal && setShowAddModal(true)}
            className="group flex aspect-square flex-col items-center justify-center rounded-2xl border-2 border-dashed border-neutral-200 bg-neutral-50/50 p-6 text-center transition-all hover:border-[#FF4F00] hover:bg-[#FFF4E0]/20"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white border border-neutral-200 shadow-2xs transition-transform group-hover:scale-110 group-hover:bg-[#FF4F00] group-hover:text-white group-hover:border-[#FF4F00]">
              <Plus className="h-6 w-6" />
            </div>
            <span className="mt-3 text-xs font-bold text-neutral-900">Add New Item</span>
            <span className="mt-0.5 text-[11px] text-neutral-400">Post product to shop</span>
          </button>

          {/* Product Cards */}
          {filteredProducts.map((p) => (
            <div
              key={p.product_id}
              data-testid={`product-card-${p.product_id}`}
              className="group relative flex flex-col overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-2xs transition-all hover:shadow-md hover:border-neutral-300"
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

                {/* Quick Delete Overlay Button */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    del(p.product_id);
                  }}
                  className="absolute bottom-2.5 right-2.5 flex h-8 w-8 items-center justify-center rounded-xl bg-white/90 backdrop-blur-xs text-neutral-600 shadow-sm opacity-0 transition-all hover:bg-rose-600 hover:text-white group-hover:opacity-100"
                  title="Delete product"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
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
                      {p.optionGroups.length} options
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
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
                    <td className="px-5 py-3.5 text-right">
                      <button
                        data-testid={`product-del-${p.product_id}`}
                        onClick={() => del(p.product_id)}
                        className="rounded-lg p-1.5 text-neutral-400 hover:bg-rose-50 hover:text-rose-600 transition-colors"
                        title="Delete product"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {filteredProducts.length === 0 && (
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
function OrdersSection() {
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
        {/* Status Filter Tabs */}
        <div className="flex gap-1.5 overflow-x-auto pb-1 text-xs font-bold scrollbar-none">
          {[
            { id: "all", label: "All Orders" },
            { id: "paid", label: "Ready to Ship" },
            { id: "shipped", label: "In Transit" },
            { id: "delivered_pending_otp", label: "Awaiting OTP" },
            { id: "delivered_confirmed", label: "Delivered" },
            { id: "completed", label: "Completed" },
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
                    <td className="px-5 py-3.5 font-bold text-[#0A0A0A]">₹{o.amount}</td>
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
   PRO SUBSCRIPTION PLAN SECTION
   ========================================================================== */
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
    console.log("[StallWise Sub] Starting subscription flow for:", interval);
    try {
      console.log("[StallWise Sub] Calling /subscription/create...");
      const { data } = await api.post("/subscription/create", { interval });
      console.log("[StallWise Sub] Server response:", JSON.stringify(data));

      console.log("[StallWise Sub] Live mode — loading Razorpay checkout.js...");
      const ok = await loadScript();
      console.log("[StallWise Sub] Razorpay script loaded:", ok, "window.Razorpay:", !!window.Razorpay);
      if (!ok || !window.Razorpay) {
        setErrorMsg("Could not load payment checkout script. Please check your internet connection and try again.");
        setSubscribing(null);
        return;
      }

      const options = {
        key: data.keyId,
        order_id: data.orderId,
        amount: data.amount * 100,
        currency: data.currency || "INR",
        name: "Stall Wise",
        description: `${data.tier} (${interval})`,
        prefill: { email: user?.email || "", name: user?.name || "" },
        theme: { color: "#FF4F00" },
        modal: {
          ondismiss: () => {
            console.log("[StallWise Sub] User dismissed Razorpay modal");
            setSubscribing(null);
          },
        },
        handler: async (res) => {
          console.log("[StallWise Sub] Payment success, verifying...", res);
          try {
            await api.post("/subscription/verify-payment", {
              razorpay_order_id: res.razorpay_order_id,
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_signature: res.razorpay_signature,
            });
            setSuccessMsg(`🎉 Stall Wise Pro (${interval}) is now active!`);
            await load();
            if (checkAuth) await checkAuth();
            if (onChange) onChange();
          } catch (e) {
            console.error("[StallWise Sub] Verify error:", e);
            setErrorMsg(formatApiError(e.response?.data?.detail) || "Payment verification failed.");
          } finally {
            setSubscribing(null);
          }
        },
      };

      console.log("[StallWise Sub] Opening Razorpay checkout with key:", data.keyId, "order:", data.orderId);
      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", function (response) {
        console.error("[StallWise Sub] Payment failed:", response.error);
        setErrorMsg(response.error?.description || "Payment failed. Please try again.");
        setSubscribing(null);
      });
      rzp.open();
    } catch (e) {
      console.error("[StallWise Sub] Subscribe error:", e, e.response?.data);
      setErrorMsg(formatApiError(e.response?.data?.detail) || "Failed to start checkout. Please try again.");
      setSubscribing(null);
    }
  };

  const active = (sub?.subscriptionStatus || user?.subscriptionStatus) === "active";

  return (
    <Panel
      title="Store Plan & Commission Options"
      subtitle="Choose between the Free Plan (10% commission on sales) or Stall Wise Pro (ad-free storefront)."
      testId="subscription-panel"
      action={
        <span
          data-testid="sub-status"
          className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider ${
            active
              ? "bg-emerald-900 text-emerald-100 border-emerald-700"
              : "bg-neutral-100 text-neutral-700 border-neutral-200"
          }`}
        >
          {active ? "⚡ Pro Active (Ad-Free Storefront)" : "Free Plan (10% Commission)"}
        </span>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-5 sm:grid-cols-2">
          {/* Monthly Card */}
          <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xs transition-all hover:border-neutral-300">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">Monthly Pro</span>
              <span className="rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold">Ad-Free</span>
            </div>
            <p className="mt-3 text-3xl font-black text-[#0A0A0A]">
              ₹{sub?.plans?.monthly || 199}
              <span className="text-xs font-medium text-neutral-500"> / month</span>
            </p>
            <ul className="mt-4 space-y-2 text-xs text-neutral-600">
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-emerald-600" /> Ad-Free Storefront (Remove all platform ads)
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-emerald-600" /> Direct bank settlements
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-emerald-600" /> Verified Pro Seller Badge & QR code
              </li>
            </ul>
            <div className="mt-6">
              <Btn 
                variant="outline" 
                data-testid="sub-monthly-btn" 
                disabled={Boolean(subscribing)}
                onClick={() => subscribe("monthly")} 
                className="w-full"
              >
                {subscribing === "monthly" ? "Opening Checkout…" : active ? "Switch to Monthly (₹199/mo)" : "Upgrade to Pro Monthly (₹199)"}
              </Btn>
            </div>
          </div>

          {/* Yearly Card */}
          <div className="relative overflow-hidden rounded-2xl border-2 border-neutral-900 bg-neutral-900 p-6 text-white shadow-md">
            <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[#FF4F00]/20 blur-2xl pointer-events-none" />
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-400">Annual Pro Plan</span>
              <span className="rounded-full bg-[#FF4F00] px-2.5 py-0.5 text-[10px] font-bold text-white">Save ₹889 (~37% off)</span>
            </div>
            <p className="mt-3 text-3xl font-black text-white">
              ₹{sub?.plans?.yearly || 1499}
              <span className="text-xs font-medium text-neutral-400"> / year</span>
            </p>
            <ul className="mt-4 space-y-2 text-xs text-neutral-300">
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Ad-Free Storefront all year long
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Save ₹889 compared to monthly billing
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-3.5 w-3.5 text-[#FF4F00]" /> Priority customer and dispute resolution
              </li>
            </ul>
            <div className="mt-6">
              <Btn 
                variant="primary" 
                data-testid="sub-yearly-btn" 
                disabled={Boolean(subscribing)}
                onClick={() => subscribe("yearly")} 
                className="w-full"
              >
                {subscribing === "yearly" ? "Opening Checkout…" : "Upgrade Annual (₹1,499/yr)"}
              </Btn>
            </div>
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
  const { user, logout, checkAuth } = useAuth();
  const [store, setStore] = useState(() => {
    try {
      const cached = localStorage.getItem("stallwise_store");
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [storeLoaded, setStoreLoaded] = useState(() => {
    try {
      return Boolean(localStorage.getItem("stallwise_store"));
    } catch {
      return false;
    }
  });
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [orderCount, setOrderCount] = useState(0);
  const [activeTab, setActiveTab] = useState("overview"); // 'overview' | 'products' | 'orders' | 'payouts' | 'settings'
  const [viewMode, setViewMode] = useState("grid");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showQrModal, setShowQrModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  useDocumentMeta({
    title: "Executive Seller Suite | Stall Wise",
    description: "Manage your storefront, catalog, order fulfillment, and direct payouts on Stall Wise.",
    path: "/dashboard",
  });

  const loadProducts = useCallback(async () => {
    try {
      const { data } = await api.get("/products");
      if (Array.isArray(data)) setProducts(data);
      else if (data?.products) setProducts(data.products);
      else setProducts([]);
    } catch {
      setProducts([]);
    }
  }, []);

  const loadStore = useCallback(async (updated, localOnly) => {
    if (updated) {
      setStore(updated);
      try {
        localStorage.setItem("stallwise_store", JSON.stringify(updated));
      } catch {}
      setStoreLoaded(true);
      return;
    }
    try {
      const { data } = await api.get("/stores/me");
      if (data) {
        setStore(data);
        try {
          localStorage.setItem("stallwise_store", JSON.stringify(data));
        } catch {}
      } else {
        // If server explicitly returns null (no store for this user)
        setStore(null);
        try {
          localStorage.removeItem("stallwise_store");
        } catch {}
      }
    } catch (err) {
      // Only set to null if backend returns a 404 (user legitimately has no store)
      if (err.response?.status === 404) {
        setStore(null);
        try {
          localStorage.removeItem("stallwise_store");
        } catch {}
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

  useEffect(() => {
    loadStore();
    loadProducts();
    loadOrders();
  }, [loadStore, loadProducts, loadOrders]);

  useEffect(() => {
    if (storeLoaded && store === null && user && !user?.hasStore) {
      navigate("/onboarding", { replace: true });
    }
  }, [storeLoaded, store, user, navigate]);

  const copyShopUrl = async () => {
    if (!store) return;
    const url = `https://stallwise.in/${store.slug}`;
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  // Executive Metrics Calculations
  const metrics = useMemo(() => {
    const isPro = user?.subscriptionStatus === "active";
    const grossRevenue = orders.reduce((sum, o) => sum + (o.amount || 0), 0);
    const completedOrders = orders.filter((o) => o.status === "completed" || o.status === "delivered_confirmed").length;
    const pendingFulfillment = orders.filter((o) => o.status === "paid" || o.status === "shipped" || o.status === "delivered_pending_otp").length;
    const aov = orders.length > 0 ? Math.round(grossRevenue / orders.length) : 0;
    const netPayout = isPro ? grossRevenue : Math.round(grossRevenue * 0.90);
    const commissionPaidOrSaved = Math.round(grossRevenue * 0.10);

    return {
      grossRevenue,
      netPayout,
      totalOrders: orderCount,
      completedOrders,
      pendingFulfillment,
      aov,
      commissionPaidOrSaved,
      isPro,
    };
  }, [orders, orderCount, user?.subscriptionStatus]);

  // Real 7-Day Performance Trend
  const performance7Days = useMemo(() => {
    const days = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().split("T")[0];
      const dayLabel = i === 0 ? "Today" : i === 1 ? "Yesterday" : d.toLocaleDateString("en-US", { weekday: "short" });

      const dayOrders = orders.filter((o) => {
        if (!o.created_at) return false;
        try {
          const od = new Date(o.created_at).toISOString().split("T")[0];
          return od === dateStr;
        } catch {
          return false;
        }
      });

      const revenue = dayOrders.reduce((sum, o) => sum + (o.amount || 0), 0);
      days.push({
        date: dateStr,
        label: dayLabel,
        orders: dayOrders.length,
        revenue,
      });
    }

    const maxRev = Math.max(...days.map((d) => d.revenue), 100);
    return { days, maxRev };
  }, [orders]);

  if (!user || !storeLoaded) {
    return (
      <div className="mk min-h-screen bg-[#F8F9FA] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-neutral-300 border-t-[#FF4F00]" />
          <span className="text-xs font-bold text-neutral-500 uppercase tracking-widest">Loading dashboard…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mk min-h-screen bg-[#F8F9FA] text-[#0A0A0A]">
      {/* QR Code Generator Modal */}
      <StoreQrModal
        isOpen={showQrModal}
        onClose={() => setShowQrModal(false)}
        storeName={store?.name}
        storeSlug={store?.slug}
      />

      {/* ====================================================================
          EXECUTIVE COMMAND TOPBAR
          ==================================================================== */}
      <header className="sticky top-0 z-40 border-b border-neutral-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          {/* Logo & Live Store Pill */}
          <div className="flex items-center gap-3.5">
            <Link to="/" className="mk-head text-lg font-black tracking-tight" data-testid="dashboard-brand-logo">
              STALL WISE<span className="text-[#FF4F00]">.</span>
            </Link>

            {store && (
              <div className="hidden sm:flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50/70 px-3 py-1 text-xs font-bold text-emerald-800">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Live Store</span>
                <span className="text-emerald-400 font-normal">|</span>
                <span className="font-mono text-emerald-700">stallwise.in/{store.slug}</span>
              </div>
            )}
            {/* Quick Upgrade Button if not Pro */}
            {user?.subscriptionStatus !== "active" && (
              <button
                type="button"
                onClick={() => {
                  setActiveTab("payouts");
                  window.scrollTo({ top: 400, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#FF4F00] to-orange-600 px-3.5 py-1.5 text-xs font-black text-white shadow-sm hover:opacity-95 hover:shadow transition-all animate-pulse"
              >
                <span>⚡ Upgrade Pro (₹199)</span>
              </button>
            )}

            {store && (
              <>
                <button
                  type="button"
                  onClick={() => setShowQrModal(true)}
                  className="hidden md:inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-700 shadow-2xs hover:bg-neutral-50 hover:border-neutral-300 transition-all"
                  title="Generate QR Code"
                >
                  <QrCode className="h-3.5 w-3.5 text-[#FF4F00]" />
                  <span>QR Code</span>
                </button>

                <button
                  type="button"
                  onClick={copyShopUrl}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-3 py-1.5 text-xs font-bold text-neutral-700 shadow-2xs hover:bg-neutral-50 hover:border-neutral-300 transition-all"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span className="text-emerald-700">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-neutral-500" />
                      <span>Share</span>
                    </>
                  )}
                </button>

                <Link
                  to={`/${store.slug}`}
                  target="_blank"
                  className="inline-flex items-center gap-1 rounded-xl bg-neutral-900 px-3.5 py-1.5 text-xs font-bold text-white shadow-2xs hover:bg-[#FF4F00] transition-all"
                >
                  <span>Visit Shop</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </>
            )}

            {/* Logout Button */}
            <button
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              data-testid="logout-btn"
              className="rounded-xl p-2 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
              title="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ====================================================================
          EXECUTIVE HERO STOREFRONT BANNER
          ==================================================================== */}
      <div className="border-b border-neutral-200/80 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            {/* Store Bio and Avatar */}
            <div className="flex items-center gap-5">
              <div className="relative">
                <div className="h-20 w-20 sm:h-24 sm:w-24 overflow-hidden rounded-2xl border-2 border-neutral-900 bg-neutral-100 shadow-md">
                  {user?.avatar ? (
                    <img
                      src={fileUrl(user.avatar)}
                      alt={store?.name || "Store Avatar"}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-neutral-800 to-neutral-950 text-white font-black text-2xl">
                      {store?.name?.slice(0, 2).toUpperCase() || "SW"}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab("settings")}
                  className="absolute -bottom-1.5 -right-1.5 flex h-7 w-7 items-center justify-center rounded-xl bg-[#FF4F00] text-white shadow-sm hover:scale-105 transition-transform"
                  title="Change Store Avatar"
                >
                  <Camera className="h-3.5 w-3.5" />
                </button>
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="mk-head text-2xl sm:text-3xl font-black tracking-tight text-[#0A0A0A]">
                    {store?.name || "My Store"}
                  </h1>
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-[11px] font-bold text-blue-700">
                    <CheckCircle2 className="h-3 w-3 text-blue-600" /> Verified Merchant
                  </span>
                </div>

                <p className="mt-1 text-xs text-neutral-500 font-mono">
                  stallwise.in/<span className="text-[#FF4F00] font-bold">{store?.slug || "store"}</span>
                </p>

                {store?.bio && (
                  <p className="mt-2 text-xs text-neutral-600 line-clamp-2 max-w-xl">
                    {store.bio}
                  </p>
                )}
              </div>
            </div>

            {/* Quick Action Button Group */}
            <div className="flex items-center gap-2.5 flex-wrap">
              <Btn
                variant="primary"
                onClick={() => {
                  setShowAddModal(true);
                  setActiveTab("products");
                }}
                className="py-2.5 px-4 shadow-sm"
              >
                <Plus className="h-4 w-4" /> Add Product
              </Btn>

              <button
                type="button"
                onClick={() => setShowQrModal(true)}
                className="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-xs sm:text-sm font-bold text-neutral-800 shadow-2xs hover:bg-neutral-100 hover:border-neutral-300 transition-all"
              >
                <QrCode className="h-4 w-4 text-[#FF4F00]" /> Store QR
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ====================================================================
          MAIN DASHBOARD BODY
          ==================================================================== */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* ================= EXECUTIVE KPI STATS BAR ================= */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Card 1: Gross Sales Volume */}
          <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-5 shadow-2xs transition-all hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">Gross Volume</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <DollarSign className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl sm:text-3xl font-black text-[#0A0A0A]">
              ₹{metrics.grossRevenue.toLocaleString()}
            </p>
            <div className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-emerald-600">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Standard Payout Rate</span>
              <span className="text-neutral-400 font-normal">· Direct to Bank</span>
            </div>
          </div>

          {/* Card 2: Total Orders */}
          <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-5 shadow-2xs transition-all hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">Total Orders</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <ShoppingBag className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl sm:text-3xl font-black text-[#0A0A0A]">
              {metrics.totalOrders}
            </p>
            <div className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-blue-600">
              <Clock className="h-3.5 w-3.5" />
              <span>{metrics.pendingFulfillment} Pending Fulfillment</span>
            </div>
          </div>

          {/* Card 3: Average Order Value */}
          <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-5 shadow-2xs transition-all hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">Average Order Value</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
                <ArrowUpRight className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl sm:text-3xl font-black text-[#0A0A0A]">
              ₹{metrics.aov}
            </p>
            <div className="mt-2 text-[11px] text-neutral-500 font-medium">
              Based on {metrics.totalOrders} customer transaction{metrics.totalOrders !== 1 ? "s" : ""}
            </div>
          </div>

          {/* Card 4: Plan Monetization / Net Earnings */}
          <div 
            onClick={() => setActiveTab("payouts")}
            className="cursor-pointer overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-5 shadow-2xs transition-all hover:shadow-md hover:border-[#FF4F00]/30"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                {"Net Seller Payout"}
              </span>
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-orange-50 text-[#FF4F00]">
                <Percent className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-2 text-2xl sm:text-3xl font-black text-emerald-600">
              ₹{metrics.netPayout.toLocaleString()}
            </p>
            <div className="mt-2 text-[11px] font-bold text-neutral-500">
              {metrics.isPro ? "90% net payout (Pro User)" : "90% net payout (Click to Upgrade Pro →)"}
            </div>
          </div>
        </div>

        {/* ================= EXECUTIVE NAVIGATION TABS ================= */}
        <div className="flex overflow-x-auto rounded-2xl border border-neutral-200 bg-white p-1.5 shadow-2xs scrollbar-none">
          {[
            { id: "overview", label: "Executive Overview", icon: TrendingUp },
            { id: "products", label: `Catalog & Products (${products.length})`, icon: Package },
            { id: "orders", label: `Fulfillment & Orders (${orderCount})`, icon: ShoppingBag },
            { id: "payouts", label: "Direct Payouts & Plan", icon: CreditCard },
            { id: "settings", label: "Store Identity", icon: Settings },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex flex-1 shrink-0 min-w-[140px] items-center justify-center gap-2 rounded-xl px-4 py-3 text-xs sm:text-sm font-bold transition-all ${
                  isActive
                    ? "bg-neutral-900 text-white shadow-sm"
                    : "text-neutral-500 hover:text-neutral-900 hover:bg-neutral-50"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-[#FF4F00]" : "text-neutral-400"}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ================= TAB CONTENTS ================= */}
        <div>
          {/* TAB 1: EXECUTIVE OVERVIEW */}
          {activeTab === "overview" && (
            <div className="space-y-8">
              {/* Activity Chart & Live Overview */}
              <div className="grid gap-6 lg:grid-cols-3">
                {/* 7-Day Performance Graph (2 cols) */}
                <div className="lg:col-span-2 overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-6 shadow-2xs">
                  <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
                    <div>
                      <h3 className="font-bold text-[#0A0A0A] text-base">Store Performance Trend</h3>
                      <p className="text-xs text-neutral-500">Live 7-day gross sales volume & order count</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Live Data
                    </span>
                  </div>

                  {/* Visual SVG Activity Graph with Real Points */}
                  <div className="my-6">
                    <div className="relative h-44 w-full">
                      <svg className="h-full w-full overflow-visible" viewBox="0 0 500 150">
                        <defs>
                          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#FF4F00" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#FF4F00" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        {/* Horizontal Grid lines */}
                        <line x1="0" y1="30" x2="500" y2="30" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="0" y1="75" x2="500" y2="75" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 3" />
                        <line x1="0" y1="120" x2="500" y2="120" stroke="#f1f5f9" strokeWidth="1" />

                        {(() => {
                          const pts = performance7Days.days.map((d, idx) => {
                            const x = Math.round((idx / 6) * 500);
                            const ratio = performance7Days.maxRev > 0 ? d.revenue / performance7Days.maxRev : 0;
                            const y = Math.round(120 - ratio * 90);
                            return { x, y, ...d };
                          });

                          const pathD = pts.reduce((acc, p, idx) => {
                            return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
                          }, "");

                          const fillD = `${pathD} L 500 120 L 0 120 Z`;

                          return (
                            <>
                              {/* Area fill */}
                              <path d={fillD} fill="url(#chartGradient)" />
                              {/* Trend line */}
                              <path
                                d={pathD}
                                fill="none"
                                stroke="#FF4F00"
                                strokeWidth="3"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                              {/* Data points */}
                              {pts.map((p, idx) => (
                                <g key={idx} className="group cursor-pointer">
                                  <circle
                                    cx={p.x}
                                    cy={p.y}
                                    r={idx === 6 ? 6 : 4.5}
                                    fill={idx === 6 ? "#0A0A0A" : "#FF4F00"}
                                    stroke="#ffffff"
                                    strokeWidth="2"
                                  />
                                </g>
                              ))}
                            </>
                          );
                        })()}
                      </svg>
                    </div>

                    {/* Day-by-Day Real Metric Cards */}
                    <div className="grid grid-cols-7 gap-1 pt-3 border-t border-neutral-100 text-center">
                      {performance7Days.days.map((d, idx) => (
                        <div
                          key={idx}
                          className={`rounded-lg p-1.5 transition-colors ${
                            idx === 6 ? "bg-neutral-900 text-white" : "hover:bg-neutral-50 text-neutral-600"
                          }`}
                        >
                          <span className={`block text-[10px] font-bold ${idx === 6 ? "text-neutral-300" : "text-neutral-400"}`}>
                            {d.label}
                          </span>
                          <span className={`block text-xs font-black mt-0.5 ${idx === 6 ? "text-white" : "text-[#0A0A0A]"}`}>
                            ₹{d.revenue.toLocaleString()}
                          </span>
                          <span className={`block text-[9px] ${idx === 6 ? "text-emerald-400" : "text-neutral-400"}`}>
                            {d.orders} ord
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Quick Action Shortcuts (1 col) */}
                <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white p-6 shadow-2xs space-y-4">
                  <h3 className="font-bold text-[#0A0A0A] text-base border-b border-neutral-100 pb-3">
                    Merchant Quick Actions
                  </h3>

                  <button
                    onClick={() => {
                      setShowAddModal(true);
                      setActiveTab("products");
                    }}
                    className="flex w-full items-center justify-between rounded-xl border border-neutral-100 bg-neutral-50/70 p-3.5 text-left transition-all hover:bg-neutral-100 hover:border-neutral-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#FF4F00]/10 text-[#FF4F00]">
                        <Plus className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="font-bold text-sm text-[#0A0A0A] block">Add New Product</span>
                        <span className="text-xs text-neutral-500">List items with custom options</span>
                      </div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-neutral-400" />
                  </button>

                  <button
                    onClick={() => setShowQrModal(true)}
                    className="flex w-full items-center justify-between rounded-xl border border-neutral-100 bg-neutral-50/70 p-3.5 text-left transition-all hover:bg-neutral-100 hover:border-neutral-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                        <QrCode className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="font-bold text-sm text-[#0A0A0A] block">Storefront QR Code</span>
                        <span className="text-xs text-neutral-500">Download for Instagram / packaging</span>
                      </div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-neutral-400" />
                  </button>

                  <button
                    onClick={() => setActiveTab("payouts")}
                    className="flex w-full items-center justify-between rounded-xl border border-neutral-100 bg-neutral-50/70 p-3.5 text-left transition-all hover:bg-neutral-100 hover:border-neutral-200"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
                        <Landmark className="h-5 w-5" />
                      </div>
                      <div>
                        <span className="font-bold text-sm text-[#0A0A0A] block">Payout Account</span>
                        <span className="text-xs text-neutral-500">Manage bank settlement details</span>
                      </div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-neutral-400" />
                  </button>
                </div>
              </div>

              {/* Products & Orders Overview Preview */}
              <ProductsSection
                hasStore={!!store}
                viewMode={viewMode}
                setViewMode={setViewMode}
                showAddModal={showAddModal}
                setShowAddModal={setShowAddModal}
                products={products}
                loadProducts={loadProducts}
              />
            </div>
          )}

          {/* TAB 2: PRODUCTS & CATALOG */}
          {activeTab === "products" && (
            <ProductsSection
              hasStore={!!store}
              viewMode={viewMode}
              setViewMode={setViewMode}
              showAddModal={showAddModal}
              setShowAddModal={setShowAddModal}
              products={products}
              loadProducts={loadProducts}
            />
          )}

          {/* TAB 3: ORDERS */}
          {activeTab === "orders" && <OrdersSection />}

          {/* TAB 4: PAYOUTS & PLAN */}
          {activeTab === "payouts" && (
            <div className="space-y-8">
              <RouteSection onChange={loadStore} />
              <SubscriptionSection user={user} onChange={checkAuth} />
            </div>
          )}

          {/* TAB 5: STORE IDENTITY */}
          {activeTab === "settings" && store && (
            <StoreSection
              store={store}
              onChange={loadStore}
              user={user}
              refreshUser={checkAuth}
            />
          )}
        </div>
      </main>
    </div>
  );
}

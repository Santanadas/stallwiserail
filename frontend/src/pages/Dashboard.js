import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
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
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Panel, Field, Btn, StatusPill, Note } from "@/components/Kit";
import ImageUpload, { fileUrl } from "@/components/ImageUpload";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

function StoreSection({ store, onChange, user, refreshUser }) {
  const [err, setErr] = useState("");
  const [saved, setSaved] = useState(false);

  if (!store) return null;

  const save = async () => {
    setErr("");
    setSaved(false);
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
    }
  };

  const setAvatar = async () => {
    await refreshUser?.();
  };

  return (
    <Panel
      title="Store settings"
      testId="store-panel"
      action={
        store?.slug ? (
          <Link
            to={`/${store.slug}`}
            data-testid="store-shop-link"
            className="inline-flex items-center gap-1.5 text-sm font-bold text-[#0A0A0A] transition-colors hover:text-[#FF4F00]"
          >
            /{store.slug} <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        ) : null
      }
    >
      <div className="mb-6">
        <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Profile photo</span>
        <div className="mt-2">
          <ImageUpload
            value={user?.avatar}
            onChange={setAvatar}
            kind="avatar"
            shape="round"
            label="Upload photo"
            testId="store-avatar"
          />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Store name"
          data-testid="store-name-edit"
          value={store?.name || ""}
          onChange={(e) => onChange({ ...store, name: e.target.value }, true)}
        />
        <Field
          label="Acceptance window (min)"
          data-testid="store-window-edit"
          type="number"
          value={store?.acceptanceWindowMinutes ?? 120}
          onChange={(e) => onChange({ ...store, acceptanceWindowMinutes: e.target.value }, true)}
        />
      </div>
      <label className="mt-4 block">
        <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Bio</span>
        <textarea
          data-testid="store-bio-edit"
          rows={3}
          placeholder="Tell buyers what you sell and how you ship."
          value={store?.bio || ""}
          onChange={(e) => onChange({ ...store, bio: e.target.value }, true)}
          className="mt-1.5 w-full resize-none border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-neutral-400 focus:border-[#FF4F00]"
        />
      </label>
      <div className="mt-5 flex items-center gap-3">
        <Btn variant="dark" data-testid="store-save-btn" onClick={save}>
          Save changes
        </Btn>
        {saved && (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-[#0B5227]">
            <Check className="h-4 w-4" /> Changes saved!
          </span>
        )}
      </div>
      {err && (
        <div className="mt-4">
          <Note tone="error">{err}</Note>
        </div>
      )}
    </Panel>
  );
}

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
      setMsg("Payouts connected — settlements go directly to your bank.");
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
    await api.delete("/seller/route");
    load();
    onChange();
  };

  return (
    <Panel
      title="Payment gateway"
      testId="route-panel"
      action={
        <span
          data-testid="route-status"
          className={`inline-flex items-center gap-1.5 border border-[#0A0A0A] px-2 py-0.5 text-xs font-bold uppercase tracking-wider ${
            route?.connected ? "bg-[#E6F6EC] text-[#0B5227]" : "bg-neutral-100 text-neutral-700"
          }`}
        >
          {route?.connected ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldOff className="h-3.5 w-3.5" />}
          {route?.connected ? "connected" : "not connected"}
        </span>
      }
    >
      <p className="mb-4 flex items-start gap-2 text-sm text-[#525252]">
        <Landmark className="mt-0.5 h-4 w-4 shrink-0 text-[#FF4F00]" />
        Marketo is a Razorpay Partner. You're onboarded as a linked account, so buyer payments settle directly to
        your own bank — with <b className="text-[#0A0A0A]">0% commission</b>. (You can configure this whenever you
        are ready).
      </p>

      {route?.connected ? (
        <div className="border-2 border-[#0A0A0A] bg-[#FAFAFA] p-5" data-testid="route-connected-card">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3 text-sm">
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Account</span>
              <p className="font-mono">••••{route.accountIdLast4}</p>
            </div>
            {route.bankLast4 && (
              <div>
                <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Bank</span>
                <p className="font-mono">••••{route.bankLast4}</p>
              </div>
            )}
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Status</span>
              <p className="font-medium">{route.status}</p>
            </div>
          </div>
          {route.mode === "mock" && (
            <p
              className="mt-4 border-2 border-[#0A0A0A] bg-[#FFF4E0] px-3 py-2 text-xs font-medium text-[#7A4A00]"
              data-testid="route-mock-note"
            >
              SIMULATED onboarding — Route isn't enabled on the platform account yet, so real payouts are held.
              Flow is live-ready.
            </p>
          )}
          <div className="mt-4">
            <Btn variant="danger" data-testid="route-disconnect-btn" onClick={disconnect}>
              Disconnect
            </Btn>
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Legal / business name"
              data-testid="route-legal"
              placeholder="Your business"
              value={form.legal_business_name}
              onChange={upd("legal_business_name")}
            />
            <Field
              label="Contact name"
              data-testid="route-contact"
              placeholder="Your name"
              value={form.contact_name}
              onChange={upd("contact_name")}
            />
            <Field
              label="Phone"
              data-testid="route-phone"
              placeholder="9876543210"
              value={form.phone}
              onChange={upd("phone")}
            />
            <Field
              label="Beneficiary name"
              data-testid="route-beneficiary"
              placeholder="Name on bank account"
              value={form.beneficiary_name}
              onChange={upd("beneficiary_name")}
            />
            <Field
              label="Bank account number"
              data-testid="route-account"
              placeholder="Account number"
              value={form.account_number}
              onChange={upd("account_number")}
            />
            <Field
              label="IFSC"
              data-testid="route-ifsc"
              placeholder="HDFC0001234"
              value={form.ifsc}
              onChange={upd("ifsc")}
            />
          </div>
          <div className="mt-5">
            <Btn variant="primary" data-testid="route-connect-btn" onClick={connect} disabled={busy}>
              {busy ? "Connecting…" : "Connect payouts"}
            </Btn>
          </div>
        </>
      )}
      {msg && (
        <div className="mt-4">
          <Note tone={msg.toLowerCase().includes("connected") ? "success" : "error"}>{msg}</Note>
        </div>
      )}
    </Panel>
  );
}

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

  const productList = Array.isArray(products) ? products : [];

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
        <p className="text-sm text-[#525252]">Create a store first.</p>
      </Panel>
    );
  }

  return (
    <Panel
      title="Store Products & Posts"
      testId="products-panel"
      action={
        <div className="flex items-center gap-3">
          <div className="flex items-center border-2 border-[#0A0A0A] bg-white">
            <button
              onClick={() => setViewMode && setViewMode("grid")}
              className={`p-1.5 transition-colors ${
                viewMode === "grid" ? "bg-[#0A0A0A] text-white" : "text-[#525252] hover:text-[#0A0A0A]"
              }`}
              title="Grid view"
            >
              <Grid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode && setViewMode("table")}
              className={`p-1.5 transition-colors ${
                viewMode === "table" ? "bg-[#0A0A0A] text-white" : "text-[#525252] hover:text-[#0A0A0A]"
              }`}
              title="Table view"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
          <Btn
            variant="primary"
            data-testid="open-add-product-btn"
            onClick={() => setShowAddModal && setShowAddModal(true)}
            className="hidden sm:inline-flex"
          >
            <Plus className="h-4 w-4" /> New Product
          </Btn>
        </div>
      }
    >
      {/* Product Creation Composer */}
      {showAddModal && (
        <div className="mb-8 border-2 border-[#0A0A0A] bg-[#FAFAFA] p-5 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]">
          <div className="mb-4 flex items-center justify-between border-b-2 border-[#0A0A0A] pb-3">
            <div className="flex items-center gap-2 font-black text-sm uppercase tracking-wider">
              <Camera className="h-4 w-4 text-[#FF4F00]" />
              <span>Post New Product</span>
            </div>
            <button
              onClick={() => setShowAddModal(false)}
              className="p-1 hover:bg-neutral-200 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mb-4">
            <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">Product photo</span>
            <div className="mt-2">
              <ImageUpload
                value={image}
                onChange={setImage}
                kind="product"
                label="Upload photo"
                testId="product-image"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field
              label="Title / Item Name"
              data-testid="product-title"
              placeholder="e.g. Handmade Ceramic Mug"
              value={form.title}
              onChange={upd("title")}
            />
            <Field
              label="Price (₹)"
              data-testid="product-price"
              type="number"
              placeholder="599"
              value={form.price}
              onChange={upd("price")}
            />
            <Field
              label="Stock (optional)"
              data-testid="product-stock"
              type="number"
              placeholder="10"
              value={form.stock}
              onChange={upd("stock")}
            />
            <Field
              label="Caption / Description"
              data-testid="product-desc"
              placeholder="Describe your item, materials & shipping..."
              value={form.description}
              onChange={upd("description")}
            />
          </div>

          <div className="mt-4">
            <Btn data-testid="add-group-btn" onClick={addGroup}>
              <Plus className="h-4 w-4" /> Option / Variant Group
            </Btn>
            {groups.map((g, i) => (
              <div key={i} className="mt-3 grid gap-3 sm:grid-cols-3">
                <Field
                  label={`Group ${i + 1} name`}
                  data-testid={`group-name-${i}`}
                  placeholder="Size, Color, etc."
                  value={g?.name || ""}
                  onChange={updGroup(i, "name")}
                />
                <div className="sm:col-span-2">
                  <Field
                    label="Options — label|priceDelta|stock, comma separated"
                    data-testid={`group-options-${i}`}
                    placeholder="S|0|10, L|50|8"
                    value={g?.optionsText || ""}
                    onChange={updGroup(i, "optionsText")}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 flex items-center gap-3">
            <Btn
              variant="primary"
              data-testid="product-create-btn"
              onClick={create}
              disabled={submitting}
            >
              {submitting ? "Posting product..." : "Publish Product"}
            </Btn>
            <Btn variant="ghost" onClick={() => setShowAddModal(false)}>
              Cancel
            </Btn>
          </div>
          {err && (
            <div className="mt-4">
              <Note tone="error">{err}</Note>
            </div>
          )}
        </div>
      )}

      {/* INSTAGRAM-STYLE GRID VIEW */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4">
          {/* Add product action card */}
          <button
            type="button"
            onClick={() => setShowAddModal && setShowAddModal(true)}
            className="group flex aspect-square flex-col items-center justify-center border-2 border-dashed border-neutral-300 bg-white p-4 text-center transition-all hover:border-[#FF4F00] hover:bg-[#FFF4E0]/30 hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-[#0A0A0A] bg-[#FAFAFA] transition-transform group-hover:scale-110 group-hover:bg-[#FF4F00] group-hover:text-white">
              <Plus className="h-6 w-6" />
            </div>
            <span className="mt-3 text-xs font-bold uppercase tracking-wider text-[#0A0A0A]">
              Post Product
            </span>
            <span className="mt-1 text-[11px] text-[#525252]">Add to store grid</span>
          </button>

          {/* Product Cards */}
          {productList.map((p) => (
            <div
              key={p.product_id}
              data-testid={`product-card-${p.product_id}`}
              className="group relative aspect-square overflow-hidden border-2 border-[#0A0A0A] bg-[#FAFAFA] shadow-[3px_3px_0px_0px_rgba(10,10,10,1)] transition-transform hover:-translate-y-0.5 hover:shadow-[5px_5px_0px_0px_rgba(10,10,10,1)]"
            >
              {p.image ? (
                <img
                  src={fileUrl(p.image)}
                  alt={p.title}
                  className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                />
              ) : (
                <div className="flex h-full w-full flex-col items-center justify-center bg-neutral-100 p-3 text-center">
                  <Package className="h-8 w-8 text-neutral-400" />
                  <span className="mt-2 text-xs font-bold text-neutral-600 line-clamp-1">{p.title}</span>
                </div>
              )}

              {/* Price badge */}
              <div className="absolute top-2 left-2 border border-[#0A0A0A] bg-[#0A0A0A] px-2 py-0.5 text-xs font-black text-white shadow-sm">
                ₹{p.price}
              </div>

              {/* Stock badge */}
              {p.stock !== null && p.stock !== undefined && (
                <div
                  className={`absolute top-2 right-2 border border-[#0A0A0A] px-1.5 py-0.5 text-[10px] font-bold ${
                    p.stock > 0 ? "bg-white text-[#0A0A0A]" : "bg-[#8A2200] text-white"
                  }`}
                >
                  {p.stock > 0 ? `${p.stock} in stock` : "Sold out"}
                </div>
              )}

              {/* Hover overlay with actions & title */}
              <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-black/90 via-black/40 to-transparent p-3 text-white opacity-0 transition-opacity group-hover:opacity-100">
                <p className="text-xs font-bold line-clamp-1">{p.title}</p>
                {p.description && <p className="text-[11px] text-neutral-300 line-clamp-1">{p.description}</p>}
                <div className="mt-2 flex items-center justify-between border-t border-white/20 pt-2">
                  <span className="text-xs font-black text-[#FF4F00]">₹{p.price}</span>
                  <button
                    type="button"
                    onClick={() => del(p.product_id)}
                    className="rounded p-1 text-white hover:bg-red-600 transition-colors"
                    title="Delete product"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TABLE VIEW */}
      {viewMode === "table" && (
        <div className="overflow-x-auto">
          <table data-testid="products-table" className="w-full min-w-[560px] border-collapse text-sm">
            <thead>
              <tr className="border-b-2 border-[#0A0A0A] text-left text-xs font-bold uppercase tracking-widest text-[#525252]">
                <th className="py-2 pr-3">Item</th>
                <th className="py-2 pr-3">Price</th>
                <th className="py-2 pr-3">Stock</th>
                <th className="py-2 pr-3">Options</th>
                <th className="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {productList.map((p) => (
                <tr
                  key={p.product_id}
                  data-testid={`product-row-${p.product_id}`}
                  className="border-b border-[#E5E5E5]"
                >
                  <td className="py-3 pr-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 shrink-0 overflow-hidden border border-[#0A0A0A] bg-[#FAFAFA]">
                        {p.image ? (
                          <img src={fileUrl(p.image)} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[10px] text-neutral-400">
                            —
                          </div>
                        )}
                      </div>
                      <div>
                        <span className="font-bold text-[#0A0A0A]">{p.title}</span>
                        {p.description && (
                          <p className="text-xs text-[#525252] line-clamp-1">{p.description}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="py-3 pr-3 font-bold">₹{p.price}</td>
                  <td className="py-3 pr-3 text-xs">
                    {p.stock !== null && p.stock !== undefined ? (
                      <span className={p.stock > 0 ? "text-[#0A0A0A]" : "text-[#8A2200] font-bold"}>
                        {p.stock} left
                      </span>
                    ) : (
                      <span className="text-neutral-400">Unlimited</span>
                    )}
                  </td>
                  <td className="py-3 pr-3 text-xs text-[#525252]">
                    {(p.optionGroups || []).map((g) => `${g?.name || "Option"} (${(g?.options || []).length})`).join(", ") || "—"}
                  </td>
                  <td className="py-3 text-right">
                    <button
                      data-testid={`product-del-${p.product_id}`}
                      onClick={() => del(p.product_id)}
                      className="p-1 text-[#8A2200] transition-colors hover:text-[#FF4F00]"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {productList.length === 0 && (
            <p className="py-6 text-center text-sm text-[#525252]">No products listed yet.</p>
          )}
        </div>
      )}
    </Panel>
  );
}

function OrdersSection() {
  const [data, setData] = useState({ orders: [], total: 0, page: 1, pages: 1 });
  const [page, setPage] = useState(1);
  const limit = 20;

  const load = useCallback(async () => {
    try {
      const { data: d } = await api.get(`/orders?page=${page}&limit=${limit}`);
      setData(d || { orders: [], total: 0, page: 1, pages: 1 });
    } catch {
      setData({ orders: [], total: 0, page: 1, pages: 1 });
    }
  }, [page]);
  useEffect(() => {
    load();
  }, [load]);

  const orders = data.orders || [];

  return (
    <Panel
      title="Orders"
      testId="orders-panel"
      action={
        <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">
          {data.total} total
        </span>
      }
    >
      <div className="overflow-x-auto">
        <table data-testid="orders-table" className="w-full min-w-[620px] border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-[#0A0A0A] text-left text-xs font-bold uppercase tracking-widest text-[#525252]">
              <th className="py-2 pr-3">Order</th>
              <th className="py-2 pr-3">Buyer</th>
              <th className="py-2 pr-3">Amount</th>
              <th className="py-2 pr-3">Status</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr
                key={o.order_id}
                data-testid={`order-row-${o.order_id}`}
                className="border-b border-[#E5E5E5]"
              >
                <td className="py-3 pr-3 font-mono text-xs">{o.order_id}</td>
                <td className="py-3 pr-3">{o.buyerName}</td>
                <td className="py-3 pr-3 font-bold">₹{o.amount}</td>
                <td className="py-3 pr-3">
                  <StatusPill status={o.status} data-testid={`order-status-${o.order_id}`} />
                </td>
                <td className="py-3 text-right">
                  <Link
                    to={`/orders/${o.order_id}`}
                    data-testid={`order-open-${o.order_id}`}
                    className="text-xs font-bold uppercase tracking-wider transition-colors hover:text-[#FF4F00]"
                  >
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {orders.length === 0 && (
        <p data-testid="orders-empty" className="pt-4 text-sm text-[#525252]">
          No orders yet.
        </p>
      )}

      {data.total > limit && (
        <div
          className="mt-5 flex items-center justify-between border-t border-[#E5E5E5] pt-4"
          data-testid="orders-pagination"
        >
          <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">
            Page {data.page} of {data.pages} · {data.total} orders
          </span>
          <div className="flex items-center gap-2">
            <button
              data-testid="orders-prev"
              disabled={data.page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="inline-flex items-center gap-1 border-2 border-[#0A0A0A] bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
            >
              <ChevronLeft className="h-3.5 w-3.5" /> Prev
            </button>
            <button
              data-testid="orders-next"
              disabled={data.page >= data.pages}
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              className="inline-flex items-center gap-1 border-2 border-[#0A0A0A] bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
            >
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </Panel>
  );
}

function SubscriptionSection({ user, onChange }) {
  const [sub, setSub] = useState(null);
  const [msg, setMsg] = useState("");
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
    setMsg("");
    try {
      const { data } = await api.post("/subscription/create", { interval });
      const ok = await loadScript();
      if (!ok) {
        setMsg("Could not load Razorpay checkout.");
        return;
      }
      const base = {
        key: data.keyId,
        name: "Marketo",
        description: `${data.tier} (${interval})`,
        prefill: { email: user?.email || "", name: user?.name || "" },
      };
      let options;
      if (data.mode === "subscription") {
        options = {
          ...base,
          subscription_id: data.subscriptionId,
          handler: () => {
            setMsg("Subscription authorized — activating shortly.");
            setTimeout(() => {
              load();
              onChange();
            }, 3000);
          },
        };
      } else {
        options = {
          ...base,
          order_id: data.orderId,
          amount: data.amount * 100,
          currency: data.currency,
          handler: async (res) => {
            try {
              await api.post("/subscription/verify-payment", {
                razorpay_order_id: res.razorpay_order_id,
                razorpay_payment_id: res.razorpay_payment_id,
                razorpay_signature: res.razorpay_signature,
              });
              setMsg(`${data.tier} is now active!`);
              load();
              onChange();
            } catch (e) {
              setMsg(formatApiError(e.response?.data?.detail));
            }
          },
        };
      }
      new window.Razorpay(options).open();
    } catch (e) {
      setMsg(formatApiError(e.response?.data?.detail));
    }
  };

  const simulate = async (status) => {
    await api.post("/subscription/simulate", { status });
    setMsg(`(test) subscription set to ${status}`);
    load();
    onChange();
  };
  const active = (sub?.subscriptionStatus || user?.subscriptionStatus) === "active";

  return (
    <Panel
      title="Subscription & Plan"
      testId="subscription-panel"
      action={
        <span
          data-testid="sub-status"
          className={`border border-[#0A0A0A] px-2 py-0.5 text-xs font-bold uppercase tracking-wider ${
            active ? "bg-[#0A0A0A] text-white" : "bg-neutral-100 text-neutral-700"
          }`}
        >
          {sub?.subscriptionStatus || user?.subscriptionStatus || "free"}
        </span>
      }
    >
      <p className="text-sm text-[#525252]">
        <b className="text-[#0A0A0A]">{sub?.premiumTier}</b> removes ads from your shop — ₹{sub?.plans?.monthly}
        /month or ₹{sub?.plans?.yearly}/year. Free tier: <b className="text-[#0A0A0A]">{sub?.freeTier}</b>.
      </p>

      {sub?.billingConfigured ? (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="border-2 border-[#0A0A0A] p-5">
            <p className="mk-head text-2xl font-black tracking-tighter">
              ₹{sub?.plans?.monthly}
              <span className="ml-1 text-sm font-medium tracking-normal text-[#525252]">/month</span>
            </p>
            <p className="mt-1 text-sm text-[#525252]">Ad-free, cancel anytime</p>
            <div className="mt-4">
              <Btn variant="ghost" data-testid="sub-monthly-btn" onClick={() => subscribe("monthly")}>
                Go monthly
              </Btn>
            </div>
          </div>
          <div className="border-2 border-[#0A0A0A] bg-[#0A0A0A] p-5 text-white">
            <p className="mk-head text-2xl font-black tracking-tighter">
              ₹{sub?.plans?.yearly}
              <span className="ml-1 text-sm font-medium tracking-normal text-neutral-400">/year</span>
            </p>
            <p className="mt-1 text-sm text-neutral-300">Best value — ad-free all year</p>
            <div className="mt-4">
              <Btn variant="primary" data-testid="sub-yearly-btn" onClick={() => subscribe("yearly")}>
                Go yearly
              </Btn>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4">
          <Note data-testid="billing-not-configured">
            Live billing not configured yet (platform Razorpay keys pending).
          </Note>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-[#E5E5E5] pt-4">
        <span className="text-xs font-bold uppercase tracking-widest text-neutral-400">Testing helpers</span>
        <button
          data-testid="sub-activate-btn"
          onClick={() => simulate("active")}
          className="text-xs font-bold uppercase tracking-wider text-neutral-500 underline transition-colors hover:text-[#FF4F00]"
        >
          simulate active
        </button>
        <button
          data-testid="sub-cancel-btn"
          onClick={() => simulate("inactive")}
          className="text-xs font-bold uppercase tracking-wider text-neutral-500 underline transition-colors hover:text-[#FF4F00]"
        >
          simulate inactive
        </button>
      </div>
      {msg && (
        <div className="mt-4">
          <Note tone="success">{msg}</Note>
        </div>
      )}
    </Panel>
  );
}

export default function Dashboard() {
  const { user, logout, checkAuth } = useAuth();
  const [store, setStore] = useState(null);
  const [storeLoaded, setStoreLoaded] = useState(false);
  const [products, setProducts] = useState([]);
  const [orderCount, setOrderCount] = useState(0);
  const [activeTab, setActiveTab] = useState("products"); // 'products' | 'orders' | 'settings' | 'payouts'
  const [viewMode, setViewMode] = useState("grid"); // 'grid' | 'table'
  const [showAddModal, setShowAddModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  useDocumentMeta({
    title: "Seller Profile & Dashboard | Marketo",
    description: "Manage your Marketo shop, products, orders and payouts.",
    path: "/dashboard",
  });

  const loadProducts = useCallback(async () => {
    try {
      const { data } = await api.get("/products");
      if (Array.isArray(data)) {
        setProducts(data);
      } else if (data && Array.isArray(data.products)) {
        setProducts(data.products);
      } else {
        setProducts([]);
      }
    } catch {
      setProducts([]);
    }
  }, []);

  const loadStore = useCallback(async (updated, localOnly) => {
    if (localOnly) {
      setStore(updated);
      return;
    }
    try {
      const { data } = await api.get("/stores/me");
      setStore(data);
    } catch {
      setStore(null);
    } finally {
      setStoreLoaded(true);
    }
  }, []);

  useEffect(() => {
    loadStore();
    loadProducts();
    // load order count
    (async () => {
      try {
        const { data: d } = await api.get("/orders?limit=1");
        setOrderCount(d?.total || 0);
      } catch {}
    })();
  }, [loadStore, loadProducts]);

  useEffect(() => {
    if (storeLoaded && store === null) {
      navigate("/onboarding", { replace: true });
    }
  }, [storeLoaded, store, navigate]);

  const copyShopUrl = () => {
    if (!store) return;
    const url = `${window.location.origin}/${store.slug}`;
    navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (!user) return null;

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="dashboard">
      {/* App Header */}
      <header className="sticky top-0 z-50 border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-5 py-3.5 md:px-8">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="mk-head text-lg font-black tracking-tighter"
              data-testid="dashboard-brand-logo"
            >
              MARKETO<span className="text-[#FF4F00]">.</span>
            </Link>
            {store && (
              <span className="hidden sm:inline-block border-l-2 border-neutral-300 pl-3 text-xs font-mono font-bold text-[#525252]">
                @{store.slug}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {store && (
              <Link
                to={`/${store.slug}`}
                target="_blank"
                className="hidden sm:inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[#0A0A0A] hover:text-[#FF4F00]"
              >
                View Shop <ExternalLink className="h-3.5 w-3.5" />
              </Link>
            )}
            <Btn
              variant="ghost"
              data-testid="logout-btn"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              <LogOut className="h-4 w-4" /> Logout
            </Btn>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-8 md:px-8 md:py-12">
        {/* ================= INSTAGRAM-STYLE PROFILE HEADER ================= */}
        {store && (
          <div className="mb-10 border-2 border-[#0A0A0A] bg-white p-6 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] sm:p-8">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
              {/* Profile Photo (PFP) with Instagram-like border ring */}
              <div className="relative mx-auto sm:mx-0 shrink-0">
                <div className="h-28 w-28 rounded-full border-4 border-[#0A0A0A] p-1 bg-white shadow-md">
                  <div className="h-full w-full overflow-hidden rounded-full bg-[#FAFAFA] flex items-center justify-center">
                    {user?.avatar ? (
                      <img
                        src={fileUrl(user.avatar)}
                        alt={store?.name || "Store"}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <Store className="h-12 w-12 text-neutral-400" />
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab("settings")}
                  className="absolute bottom-1 right-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00] text-white shadow hover:scale-110 transition-transform"
                  title="Change profile photo"
                >
                  <Camera className="h-4 w-4" />
                </button>
              </div>

              {/* Profile details */}
              <div className="flex-1 text-center sm:text-left">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                    <h1 className="mk-head text-2xl font-black tracking-tight sm:text-3xl">
                      {store?.name || "My Store"}
                    </h1>
                    <span className="font-mono text-sm font-bold text-[#FF4F00]">
                      @{store?.slug || "store"}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center justify-center gap-2">
                    <Btn
                      variant="primary"
                      onClick={() => {
                        setShowAddModal(true);
                        setActiveTab("products");
                      }}
                      className="px-4 py-2 text-xs"
                    >
                      <Plus className="h-4 w-4" /> Add Product
                    </Btn>

                    <button
                      type="button"
                      onClick={copyShopUrl}
                      className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5 hover:bg-[#FAFAFA]"
                    >
                      {copied ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-[#0B5227]" /> Copied!
                        </>
                      ) : (
                        <>
                          <Share2 className="h-3.5 w-3.5" /> Share Shop
                        </>
                      )}
                    </button>

                    <Link
                      to={`/${store?.slug || ""}`}
                      className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-3 py-2 text-xs font-bold uppercase tracking-wider text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00]"
                    >
                      Visit <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>

                {/* Stats row (Instagram-style) */}
                <div className="my-4 flex items-center justify-center sm:justify-start gap-6 border-y border-neutral-100 py-3 text-sm">
                  <div>
                    <span className="font-black text-[#0A0A0A]">{(products || []).length}</span>{" "}
                    <span className="text-[#525252]">products</span>
                  </div>
                  <div>
                    <span className="font-black text-[#0A0A0A]">{orderCount}</span>{" "}
                    <span className="text-[#525252]">orders</span>
                  </div>
                  <div>
                    <span className="font-black text-[#0B5227]">0%</span>{" "}
                    <span className="text-[#525252]">commission</span>
                  </div>
                </div>

                {/* Bio block */}
                <div className="space-y-1 text-sm">
                  {store?.bio ? (
                    <p className="text-[#525252] leading-relaxed max-w-xl">{store.bio}</p>
                  ) : (
                    <p className="text-xs italic text-neutral-400">
                      No store bio yet. Click "Edit Store" in settings to tell buyers what you sell.
                    </p>
                  )}
                  <p className="text-xs font-mono font-bold text-[#0A0A0A] pt-1">
                    🔗 marketo.com/{store?.slug}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= INSTAGRAM-STYLE NAVIGATION TABS ================= */}
        <div className="mb-6 flex border-b-2 border-[#0A0A0A] bg-white">
          <button
            onClick={() => setActiveTab("products")}
            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-black uppercase tracking-wider transition-colors ${
              activeTab === "products"
                ? "border-b-4 border-[#FF4F00] bg-[#FAFAFA] text-[#0A0A0A]"
                : "text-neutral-500 hover:text-[#0A0A0A]"
            }`}
          >
            <Grid className="h-4 w-4" /> Products ({products.length})
          </button>
          <button
            onClick={() => setActiveTab("orders")}
            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-black uppercase tracking-wider transition-colors ${
              activeTab === "orders"
                ? "border-b-4 border-[#FF4F00] bg-[#FAFAFA] text-[#0A0A0A]"
                : "text-neutral-500 hover:text-[#0A0A0A]"
            }`}
          >
            <ShoppingBag className="h-4 w-4" /> Orders ({orderCount})
          </button>
          <button
            onClick={() => setActiveTab("settings")}
            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-black uppercase tracking-wider transition-colors ${
              activeTab === "settings"
                ? "border-b-4 border-[#FF4F00] bg-[#FAFAFA] text-[#0A0A0A]"
                : "text-neutral-500 hover:text-[#0A0A0A]"
            }`}
          >
            <Settings className="h-4 w-4" /> Store Settings
          </button>
          <button
            onClick={() => setActiveTab("payouts")}
            className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-black uppercase tracking-wider transition-colors ${
              activeTab === "payouts"
                ? "border-b-4 border-[#FF4F00] bg-[#FAFAFA] text-[#0A0A0A]"
                : "text-neutral-500 hover:text-[#0A0A0A]"
            }`}
          >
            <CreditCard className="h-4 w-4" /> Payouts & Plan
          </button>
        </div>

        {/* ================= TAB CONTENTS ================= */}
        <div className="space-y-8">
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

          {activeTab === "orders" && <OrdersSection />}

          {activeTab === "settings" && store && (
            <StoreSection
              store={store}
              onChange={loadStore}
              user={user}
              refreshUser={checkAuth}
            />
          )}

          {activeTab === "payouts" && (
            <>
              <RouteSection onChange={loadStore} />
              <SubscriptionSection user={user} onChange={checkAuth} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

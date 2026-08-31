import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  X,
  Plus,
  Trash2,
  Star,
  ImagePlus,
  Loader2,
  GripVertical,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import { Btn, Note } from "@/components/Kit";

const MAX_PHOTOS = 6;

const blankGroup = () => ({ name: "", options: [{ label: "", priceDelta: "", stock: "" }] });

const PAYMENT_OPTIONS = [
  {
    id: "online",
    label: "Online payment",
    hint: "UPI, cards, netbanking and wallets via Razorpay. Settles to your bank.",
  },
  {
    id: "cod",
    label: "Cash on delivery",
    hint: "You collect cash at handover. Buyers only see this if you enable it.",
  },
];

function emptyForm() {
  return {
    title: "",
    description: "",
    price: "",
    stock: "",
    active: true,
    images: [],
    groups: [],
    paymentMethods: ["online"],
  };
}

function formFromProduct(p) {
  if (!p) return emptyForm();
  const images = Array.isArray(p.images) && p.images.length ? p.images : p.image ? [p.image] : [];
  return {
    title: p.title || "",
    description: p.description || "",
    price: p.price != null ? String(p.price) : "",
    stock: p.stock != null ? String(p.stock) : "",
    active: p.active !== false,
    images,
    paymentMethods: (p.paymentMethods && p.paymentMethods.length) ? [...p.paymentMethods] : ["online"],
    groups: (p.optionGroups || []).map((g) => ({
      name: g.name || "",
      options: (g.options || []).map((o) => ({
        label: o.label || "",
        priceDelta: o.priceDelta ? String(o.priceDelta) : "",
        stock: o.stock != null ? String(o.stock) : "",
      })),
    })),
  };
}

/* ---------------- Photo grid ---------------- */
function PhotoGrid({ images, setImages }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const pick = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setErr("");
    setBusy(true);
    const room = MAX_PHOTOS - images.length;
    const uploaded = [];
    for (const f of files.slice(0, room)) {
      try {
        const fd = new FormData();
        fd.append("file", f);
        const { data } = await api.post("/uploads/image?kind=product", fd);
        if (data?.path) uploaded.push(data.path);
      } catch (e2) {
        setErr(formatApiError(e2.response?.data?.detail) || "Upload failed.");
      }
    }
    if (uploaded.length) setImages([...images, ...uploaded]);
    setBusy(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  const removeAt = (i) => setImages(images.filter((_, idx) => idx !== i));
  const makeCover = (i) => {
    if (i === 0) return;
    const next = [...images];
    const [x] = next.splice(i, 1);
    next.unshift(x);
    setImages(next);
  };

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {images.map((src, i) => (
          <div
            key={src + i}
            className="group relative aspect-square overflow-hidden rounded-xl border border-neutral-200 bg-neutral-100"
          >
            <img src={fileUrl(src)} alt="" className="h-full w-full object-cover" />
            {i === 0 && (
              <span className="absolute left-1.5 top-1.5 inline-flex items-center gap-1 rounded-md bg-[#FF4F00] px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-white">
                <Star className="h-3 w-3 fill-white" /> Cover
              </span>
            )}
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-1 bg-gradient-to-t from-black/60 to-transparent p-1.5 opacity-0 transition-opacity group-hover:opacity-100">
              {i !== 0 ? (
                <button
                  type="button"
                  onClick={() => makeCover(i)}
                  className="rounded-md bg-white/90 px-1.5 py-0.5 text-[10px] font-bold text-neutral-800 hover:bg-white"
                >
                  Make cover
                </button>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={() => removeAt(i)}
                aria-label="Remove photo"
                className="rounded-md bg-white/90 p-1 text-rose-600 hover:bg-white"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}

        {images.length < MAX_PHOTOS && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="flex aspect-square flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-neutral-300 bg-neutral-50 text-neutral-500 transition-colors hover:border-[#FF4F00] hover:text-[#FF4F00] disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-6 w-6 animate-spin" /> : <ImagePlus className="h-6 w-6" />}
            <span className="text-[11px] font-bold">{busy ? "Uploading…" : "Add photo"}</span>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/png,image/jpeg,image/gif,image/webp"
        onChange={pick}
        className="hidden"
      />
      <p className="mt-2 text-xs text-neutral-500">
        Up to {MAX_PHOTOS} photos · PNG, JPG, GIF or WEBP · 5MB each. The first photo is your cover.
      </p>
      {err && <p className="mt-1 text-xs font-medium text-[#8A2200]">{err}</p>}
    </div>
  );
}

/* ---------------- Section shell ---------------- */
function Section({ step, title, hint, children }) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div className="mb-4 flex items-baseline gap-2.5">
        <span className="mk-head flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-neutral-900 text-xs font-black text-white">
          {step}
        </span>
        <div>
          <h3 className="mk-head text-sm font-black tracking-tight text-[#0A0A0A]">{title}</h3>
          {hint && <p className="text-xs text-neutral-500">{hint}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

const inputCls =
  "w-full rounded-xl border border-neutral-200 bg-white px-3.5 py-2.5 text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10";
const labelCls = "mb-1.5 block text-xs font-bold uppercase tracking-wider text-neutral-600";

/* ---------------- Editor ---------------- */
export default function ProductEditor({ open, product, onClose, onSaved }) {
  const [form, setForm] = useState(emptyForm);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const editing = Boolean(product);

  useEffect(() => {
    if (open) {
      setForm(formFromProduct(product));
      setErr("");
    }
  }, [open, product]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const setImages = (imgs) => set("images", imgs);

  const addGroup = () => set("groups", [...form.groups, blankGroup()]);
  const removeGroup = (gi) => set("groups", form.groups.filter((_, i) => i !== gi));
  const setGroupName = (gi, name) =>
    set("groups", form.groups.map((g, i) => (i === gi ? { ...g, name } : g)));
  const addOption = (gi) =>
    set("groups", form.groups.map((g, i) =>
      i === gi ? { ...g, options: [...g.options, { label: "", priceDelta: "", stock: "" }] } : g));
  const removeOption = (gi, oi) =>
    set("groups", form.groups.map((g, i) =>
      i === gi ? { ...g, options: g.options.filter((_, j) => j !== oi) } : g));
  const setOption = (gi, oi, k, v) =>
    set("groups", form.groups.map((g, i) =>
      i === gi
        ? { ...g, options: g.options.map((o, j) => (j === oi ? { ...o, [k]: v } : o)) }
        : g));

  const groupsPayload = useMemo(
    () =>
      form.groups
        .map((g) => ({
          name: g.name.trim(),
          options: g.options
            .filter((o) => o.label.trim())
            .map((o) => ({
              label: o.label.trim(),
              priceDelta: Number(o.priceDelta || 0),
              stock: o.stock === "" ? null : Number(o.stock),
            })),
        }))
        .filter((g) => g.name && g.options.length),
    [form.groups]
  );

  const togglePayment = (id) =>
    set(
      "paymentMethods",
      form.paymentMethods.includes(id)
        ? form.paymentMethods.filter((m) => m !== id)
        : [...form.paymentMethods, id]
    );

  const submit = async () => {
    setErr("");
    if (!form.title.trim()) return setErr("Add a product title.");
    if (!form.price || Number(form.price) <= 0) return setErr("Add a price greater than ₹0.");
    if (!form.paymentMethods.length) return setErr("Pick at least one way buyers can pay.");
    setSaving(true);
    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      stock: form.stock === "" ? null : Number(form.stock),
      active: form.active,
      image: form.images[0] || null,
      images: form.images,
      paymentMethods: form.paymentMethods,
      optionGroups: groupsPayload,
    };
    try {
      if (editing) await api.put(`/products/${product.product_id}`, payload);
      else await api.post("/products", payload);
      onSaved?.();
      onClose();
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || "Could not save the product.");
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex justify-center overflow-y-auto bg-neutral-900/50 backdrop-blur-sm p-0 sm:p-6">
      <div className="mk relative w-full max-w-3xl self-start bg-[#F8F9FA] shadow-2xl sm:my-2 sm:rounded-2xl">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white px-5 py-4 sm:rounded-t-2xl sm:px-6">
          <div>
            <h2 className="mk-head text-lg font-black tracking-tight text-[#0A0A0A]">
              {editing ? "Edit product" : "List a new product"}
            </h2>
            <p className="text-xs text-neutral-500">
              {editing ? product.title : "Add it to your storefront in a few steps."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 px-4 py-5 sm:px-6">
          <Section step={1} title="Photos" hint="Show the product from a few angles.">
            <PhotoGrid images={form.images} setImages={setImages} />
          </Section>

          <Section step={2} title="Product details">
            <div className="space-y-4">
              <div>
                <label className={labelCls}>Title</label>
                <input
                  data-testid="product-title"
                  className={inputCls}
                  placeholder="e.g. Handwoven Cotton Table Runner"
                  value={form.title}
                  maxLength={200}
                  onChange={(e) => set("title", e.target.value)}
                />
              </div>
              <div>
                <label className={labelCls}>Description</label>
                <textarea
                  data-testid="product-desc"
                  rows={4}
                  className={inputCls}
                  placeholder="Materials, dimensions, care instructions, what makes it special…"
                  value={form.description}
                  maxLength={2000}
                  onChange={(e) => set("description", e.target.value)}
                />
              </div>
            </div>
          </Section>

          <Section step={3} title="Price & inventory">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={labelCls}>Price (₹)</label>
                <input
                  data-testid="product-price"
                  type="number"
                  min="1"
                  inputMode="decimal"
                  className={inputCls}
                  placeholder="599"
                  value={form.price}
                  onChange={(e) => set("price", e.target.value)}
                />
              </div>
              <div>
                <label className={labelCls}>Stock</label>
                <input
                  data-testid="product-stock"
                  type="number"
                  min="0"
                  inputMode="numeric"
                  className={inputCls}
                  placeholder="Leave blank for unlimited"
                  value={form.stock}
                  onChange={(e) => set("stock", e.target.value)}
                />
              </div>
            </div>
            <label className="mt-4 flex items-center gap-3 rounded-xl border border-neutral-200 bg-neutral-50/60 p-3.5 cursor-pointer">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(e) => set("active", e.target.checked)}
                className="h-4 w-4 shrink-0 accent-[#FF4F00]"
              />
              <span className="text-sm">
                <span className="font-bold text-[#0A0A0A]">Visible in your shop</span>
                <span className="block text-xs text-neutral-500">Uncheck to save as a hidden draft.</span>
              </span>
            </label>
          </Section>

          <Section
            step={4}
            title="How buyers can pay"
            hint="Turn off cash on delivery and buyers won't see it for this item."
          >
            <div className="space-y-3">
              {PAYMENT_OPTIONS.map((opt) => {
                const on = form.paymentMethods.includes(opt.id);
                return (
                  <label
                    key={opt.id}
                    data-testid={`payment-${opt.id}`}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors ${
                      on ? "border-[#FF4F00] bg-[#FF4F00]/[0.04]" : "border-neutral-200 bg-white hover:border-neutral-300"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => togglePayment(opt.id)}
                      className="mt-0.5 h-4 w-4 shrink-0 accent-[#FF4F00]"
                    />
                    <span className="text-sm">
                      <span className="font-bold text-[#0A0A0A]">{opt.label}</span>
                      <span className="mt-0.5 block text-xs text-neutral-500">{opt.hint}</span>
                    </span>
                  </label>
                );
              })}
              {!form.paymentMethods.length && (
                <p className="text-xs font-bold text-[#8A2200]">Pick at least one — buyers need a way to pay.</p>
              )}
              {form.paymentMethods.length === 1 && form.paymentMethods[0] === "cod" && (
                <p className="text-xs text-neutral-500">
                  Cash only — this item won't be payable online, and can't be bought in the same
                  order as online-only items.
                </p>
              )}
            </div>
          </Section>

          <Section
            step={5}
            title="Variants"
            hint="Optional — sizes, colours, or materials buyers choose between."
          >
            <div className="space-y-4">
              {form.groups.map((g, gi) => (
                <div key={gi} className="rounded-xl border border-neutral-200 bg-neutral-50/50 p-4">
                  <div className="flex items-center gap-2">
                    <GripVertical className="h-4 w-4 shrink-0 text-neutral-300" />
                    <input
                      className={`${inputCls} bg-white`}
                      placeholder="Option name — e.g. Size"
                      value={g.name}
                      onChange={(e) => setGroupName(gi, e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => removeGroup(gi)}
                      className="shrink-0 rounded-lg p-2 text-neutral-400 hover:bg-rose-50 hover:text-rose-600"
                      aria-label="Remove variant group"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="mt-3 space-y-2">
                    <div className="hidden grid-cols-[1fr_5.5rem_5.5rem_2rem] gap-2 px-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400 sm:grid">
                      <span>Choice</span>
                      <span>+ ₹</span>
                      <span>Stock</span>
                      <span />
                    </div>
                    {g.options.map((o, oi) => (
                      <div key={oi} className="grid grid-cols-[1fr_4.5rem_4.5rem_2rem] items-center gap-2 sm:grid-cols-[1fr_5.5rem_5.5rem_2rem]">
                        <input
                          className={`${inputCls} bg-white py-2`}
                          placeholder="e.g. Large"
                          value={o.label}
                          onChange={(e) => setOption(gi, oi, "label", e.target.value)}
                        />
                        <input
                          className={`${inputCls} bg-white py-2`}
                          type="number"
                          placeholder="0"
                          value={o.priceDelta}
                          onChange={(e) => setOption(gi, oi, "priceDelta", e.target.value)}
                        />
                        <input
                          className={`${inputCls} bg-white py-2`}
                          type="number"
                          placeholder="∞"
                          value={o.stock}
                          onChange={(e) => setOption(gi, oi, "stock", e.target.value)}
                        />
                        <button
                          type="button"
                          onClick={() => removeOption(gi, oi)}
                          className="rounded-lg p-1.5 text-neutral-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-30"
                          disabled={g.options.length <= 1}
                          aria-label="Remove choice"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => addOption(gi)}
                      className="mt-1 inline-flex items-center gap-1.5 text-xs font-bold text-[#FF4F00] hover:underline"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add choice
                    </button>
                  </div>
                </div>
              ))}

              <Btn variant="ghost" onClick={addGroup} data-testid="add-group-btn">
                <Plus className="h-4 w-4" /> Add variant group
              </Btn>
            </div>
          </Section>

          {err && <Note tone="error">{err}</Note>}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 z-10 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-5 py-4 sm:rounded-b-2xl sm:px-6">
          <Btn variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Btn>
          <Btn variant="primary" onClick={submit} disabled={saving} data-testid="product-save-btn">
            {saving ? "Saving…" : editing ? "Save changes" : "Publish product"}
          </Btn>
        </div>
      </div>
    </div>,
    document.body
  );
}

import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Btn, Note } from "@/components/Kit";
import { Card } from "./Pieces";

/** Delivery, tax and alert preferences — all persisted on the store row. */

function Toggle({ on, onChange, title, desc }) {
  return (
    <label className="flex cursor-pointer items-start gap-3.5 border-b border-neutral-100 py-3.5 last:border-b-0">
      <div className="flex-1">
        <div className="text-[13px] font-bold text-[#0A0A0A]">{title}</div>
        <div className="mt-0.5 text-xs font-medium leading-snug text-neutral-500">{desc}</div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        onClick={() => onChange(!on)}
        className={`relative h-[23px] w-10 shrink-0 rounded-full transition-colors ${on ? "bg-[#FF4F00]" : "bg-neutral-200"}`}
      >
        <span className={`absolute top-[2.5px] h-[18px] w-[18px] rounded-full bg-white transition-all ${on ? "left-[19.5px]" : "left-[2.5px]"}`} />
      </button>
    </label>
  );
}

const inputCls =
  "w-full rounded-xl border border-neutral-200 bg-white px-3.5 py-2.5 text-sm text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10";
const labelCls = "mb-1.5 block text-xs font-bold uppercase tracking-wider text-neutral-600";

export default function ShopSettings({ store, onSaved }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (!store) return;
    setForm({
      deliveryFee: store.deliveryFee ?? 0,
      freeDeliveryAbove: store.freeDeliveryAbove ?? "",
      dispatchDays: store.dispatchDays ?? 2,
      gstin: store.gstin ?? "",
      hsnCode: store.hsnCode ?? "",
      notifyNewOrder: store.notifyNewOrder !== false,
      notifyDailySummary: !!store.notifyDailySummary,
      notifyWeeklyDigest: !!store.notifyWeeklyDigest,
    });
  }, [store]);

  if (!form) return null;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const { data } = await api.put("/stores/me", {
        deliveryFee: Number(form.deliveryFee) || 0,
        freeDeliveryAbove: form.freeDeliveryAbove === "" ? null : Number(form.freeDeliveryAbove),
        dispatchDays: Number(form.dispatchDays) || 0,
        gstin: form.gstin.trim(),
        hsnCode: form.hsnCode.trim(),
        notifyNewOrder: form.notifyNewOrder,
        notifyDailySummary: form.notifyDailySummary,
        notifyWeeklyDigest: form.notifyWeeklyDigest,
      });
      onSaved?.(data);
      setMsg({ tone: "success", text: "Saved." });
    } catch (e) {
      setMsg({ tone: "error", text: formatApiError(e.response?.data?.detail) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <Card title="Delivery" hint="Shown to buyers at checkout" testId="settings-delivery">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className={labelCls}>Delivery charge (₹)</label>
            <input type="number" min="0" inputMode="decimal" className={inputCls}
              data-testid="setting-delivery-fee"
              value={form.deliveryFee} onChange={(e) => set("deliveryFee", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Free delivery above (₹)</label>
            <input type="number" min="0" inputMode="decimal" className={inputCls}
              placeholder="Leave blank for none"
              value={form.freeDeliveryAbove} onChange={(e) => set("freeDeliveryAbove", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Dispatch within (days)</label>
            <input type="number" min="0" inputMode="numeric" className={inputCls}
              value={form.dispatchDays} onChange={(e) => set("dispatchDays", e.target.value)} />
          </div>
        </div>
      </Card>

      <Card title="Tax &amp; invoicing" hint="Only needed once you are registered" testId="settings-tax">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={labelCls}>GSTIN</label>
            <input className={inputCls} placeholder="e.g. 32AABCU9603R1ZM" maxLength={20}
              data-testid="setting-gstin"
              value={form.gstin} onChange={(e) => set("gstin", e.target.value.toUpperCase())} />
            <p className="mt-1 text-xs text-neutral-400">Required once turnover crosses ₹40 lakh.</p>
          </div>
          <div>
            <label className={labelCls}>Default HSN code</label>
            <input className={inputCls} placeholder="e.g. 5702" maxLength={12}
              value={form.hsnCode} onChange={(e) => set("hsnCode", e.target.value)} />
          </div>
        </div>
      </Card>

      <Card title="Notifications" hint="Sent to your account email" testId="settings-notifications">
        <Toggle on={form.notifyNewOrder} onChange={(v) => set("notifyNewOrder", v)}
          title="Email me when an order comes in"
          desc="Sent the moment a buyer pays, so you can start packing." />
        <Toggle on={form.notifyDailySummary} onChange={(v) => set("notifyDailySummary", v)}
          title="Daily summary"
          desc="One message each evening with the day's orders and anything left to ship." />
        <Toggle on={form.notifyWeeklyDigest} onChange={(v) => set("notifyWeeklyDigest", v)}
          title="Weekly insights digest"
          desc="Best sellers, repeat buyers and what ran out of stock." />
      </Card>

      {msg && <Note tone={msg.tone}>{msg.text}</Note>}

      <div className="flex justify-end">
        <Btn variant="primary" onClick={save} disabled={saving} data-testid="save-shop-settings">
          {saving ? "Saving…" : "Save changes"}
        </Btn>
      </div>
    </div>
  );
}

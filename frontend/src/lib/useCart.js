import { useCallback, useEffect, useState } from "react";

/**
 * Cart state for one storefront, persisted to localStorage.
 *
 * The cart used to live in Shop.js component state, which was fine while the
 * whole shop was a single page. Now that each product has its own URL the cart
 * has to survive navigation, so it lives here and is keyed per store — one
 * seller's cart never leaks into another's.
 */
const key = (storeSlug) => `stallwise_cart_${storeSlug}`;

function read(storeSlug) {
  try {
    const raw = localStorage.getItem(key(storeSlug));
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function useCart(storeSlug) {
  const [cart, setCart] = useState(() => (storeSlug ? read(storeSlug) : []));

  // Re-hydrate when the shop changes.
  useEffect(() => {
    setCart(storeSlug ? read(storeSlug) : []);
  }, [storeSlug]);

  useEffect(() => {
    if (!storeSlug) return;
    try {
      if (cart.length) localStorage.setItem(key(storeSlug), JSON.stringify(cart));
      else localStorage.removeItem(key(storeSlug));
    } catch {}
  }, [cart, storeSlug]);

  const addItem = useCallback((item) => {
    setCart((prev) => {
      // Same product + same option choices collapses into one line.
      const sig = JSON.stringify(item.optionSelections || {});
      const i = prev.findIndex(
        (c) => c.productId === item.productId && JSON.stringify(c.optionSelections || {}) === sig
      );
      if (i >= 0) {
        const next = [...prev];
        next[i] = { ...next[i], quantity: Math.min((next[i].quantity || 1) + (item.quantity || 1), 999) };
        return next;
      }
      return [...prev, { ...item, quantity: item.quantity || 1 }];
    });
  }, []);

  const removeItem = useCallback((i) => setCart((prev) => prev.filter((_, idx) => idx !== i)), []);

  const setQty = useCallback((i, q) => {
    setCart((prev) =>
      q < 1
        ? prev.filter((_, idx) => idx !== i)
        : prev.map((c, idx) => (idx === i ? { ...c, quantity: Math.min(q, 999) } : c))
    );
  }, []);

  const clear = useCallback(() => setCart([]), []);

  const cartTotal = cart.reduce((s, c) => s + (c.unitPrice || 0) * (c.quantity || 1), 0);
  const cartCount = cart.reduce((s, c) => s + (c.quantity || 1), 0);

  // A payment method is offered only if every item in the cart accepts it.
  const allowedPayments = cart.reduce(
    (acc, c) => acc.filter((m) => (c.paymentMethods || ["online"]).includes(m)),
    ["online", "cod"]
  );

  return { cart, addItem, removeItem, setQty, clear, cartTotal, cartCount, allowedPayments };
}

/** Shared helper: unit price including the selected option deltas. */
export function unitPriceFor(product, selections = {}) {
  let price = Number(product?.price || 0);
  (product?.optionGroups || []).forEach((g) => {
    if (!g?.name) return;
    const opt = (g.options || []).find((o) => o?.label === selections[g.name]);
    if (opt) price += Number(opt.priceDelta || 0);
  });
  return price;
}

/** Shared helper: is this product buyable at all? */
export function isSoldOut(product) {
  if (product?.stock === 0) return true;
  const groups = product?.optionGroups || [];
  if (groups.length && groups.every((g) => (g.options || []).every((o) => o.stock === 0))) return true;
  return false;
}

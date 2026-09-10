/**
 * Catalogue vocabulary shared by the product editor, the product page and the
 * storefront grid.
 *
 * Category ids must match PRODUCT_CATEGORIES in backend/server.py — the server
 * drops any id it doesn't know. The spec suggestions are only prompts: a seller
 * can name a specification anything.
 */
export const CATEGORIES = [
  { id: "fashion", label: "Clothing & fashion", specs: ["Fabric", "Fit", "Pattern", "Sleeve length", "Neck style", "Occasion", "Wash care"] },
  { id: "footwear", label: "Footwear", specs: ["Material", "Sole", "Closure", "Occasion"] },
  { id: "jewellery", label: "Jewellery & accessories", specs: ["Material", "Plating", "Stone", "Dimensions"] },
  { id: "beauty", label: "Beauty & personal care", specs: ["Net quantity", "Skin / hair type", "Key ingredients", "Shelf life"] },
  // FSSAI rules require a food business to show its licence number when it sells online.
  { id: "food", label: "Food & drinks", specs: ["Net quantity", "Ingredients", "Veg / non-veg", "Shelf life", "FSSAI licence no."] },
  { id: "home", label: "Home & kitchen", specs: ["Material", "Dimensions", "Weight", "Care instructions"] },
  { id: "electronics", label: "Electronics & gadgets", specs: ["Model number", "Warranty", "Power", "In the box"] },
  { id: "handmade", label: "Handmade & crafts", specs: ["Material", "Technique", "Dimensions", "Care instructions"] },
  { id: "books", label: "Books & stationery", specs: ["Author", "Language", "Pages", "Publisher"] },
  { id: "toys", label: "Toys & baby", specs: ["Age range", "Material", "Safety standard", "In the box"] },
  { id: "health", label: "Health & wellness", specs: ["Net quantity", "Ingredients", "How to use", "Shelf life"] },
  { id: "art", label: "Art & decor", specs: ["Medium", "Dimensions", "Framed"] },
  { id: "other", label: "Something else", specs: ["Material", "Dimensions", "Weight"] },
];

export const CONDITIONS = [
  { id: "new", label: "New" },
  { id: "used_like_new", label: "Used — like new" },
  { id: "used_good", label: "Used — good" },
  { id: "refurbished", label: "Refurbished" },
];

export const categoryLabel = (id) => CATEGORIES.find((c) => c.id === id)?.label || "";
export const conditionLabel = (id) => CONDITIONS.find((c) => c.id === id)?.label || "New";

/**
 * Whole-number percentage off MRP, or 0 when there's no real discount.
 * Rounded down so a buyer is never promised more off than they get.
 */
export function percentOff(price, mrp) {
  const p = Number(price) || 0;
  const m = Number(mrp) || 0;
  if (!m || p <= 0 || m <= p) return 0;
  return Math.floor(((m - p) / m) * 100);
}

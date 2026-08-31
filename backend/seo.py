"""Server-rendered SEO for the single-page app.

The SPA sets its own <title>/meta once React boots, which is fine for Google's
rendering pass but useless for everything that never runs JavaScript — the
Facebook / WhatsApp / X / LinkedIn / Slack / Discord unfurlers, and any crawler
on its first pass. Without this, every seller's shop link shares the homepage's
title, description and image.

So for HTML navigations we take the built dist/index.html and swap in the tags
that belong to the requested route before sending it.
"""
import html
import os
import re
from typing import Iterable, Optional

SITE_URL = (os.environ.get("SITE_URL") or "https://stallwise.in").rstrip("/")
SITE_NAME = "Stall Wise"
DESC_MAX = 155

# Drop a 1200x630 og-default.png into frontend/public/ and it is picked up
# automatically. Until then we emit no og:image rather than a broken URL —
# unfurlers show a bare card for a 404 image, which looks worse than none.
_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
DEFAULT_OG_IMAGE = (
    f"{SITE_URL}/og-default.png" if os.path.isfile(os.path.join(_DIST, "og-default.png")) else None
)

# Tags this module owns. They are stripped from the base document before the
# freshly built block is injected, so nothing is ever duplicated.
_OWNED = [
    re.compile(r"<title>.*?</title>", re.I | re.S),
    re.compile(r'<meta\s+name="description"[^>]*>', re.I),
    re.compile(r'<meta\s+name="keywords"[^>]*>', re.I),
    re.compile(r'<meta\s+name="robots"[^>]*>', re.I),
    re.compile(r'<link\s+rel="canonical"[^>]*>', re.I),
    re.compile(r'<meta\s+property="og:[^"]*"[^>]*>', re.I),
    re.compile(r'<meta\s+name="twitter:[^"]*"[^>]*>', re.I),
]

# Routes that must never be indexed: private, transactional or duplicate.
NOINDEX_PREFIXES = (
    "dashboard", "onboarding", "login", "forgot-password", "reset-password",
    "verify-email", "order/", "orders/", "auth",
)

STATIC_PAGES = {
    "": {
        "title": "Stall Wise | Direct-Payout Marketplace — Open Your Online Store",
        "description": (
            "Open your own shop at stallwise.in/your-name, list products with custom "
            "variants, and get paid straight into your bank account via Razorpay."
        ),
    },
    "about": {
        "title": "About Stall Wise | Direct-Payout Marketplace for Small Sellers",
        "description": (
            "Stall Wise lets anyone open an online shop in minutes and get paid directly "
            "into their linked bank account — no holding periods, no manual withdrawals."
        ),
    },
    "contact": {
        "title": "Contact Stall Wise | Seller & Buyer Support",
        "description": "Get help with your Stall Wise storefront, orders, payouts or account.",
    },
    "terms": {
        "title": "Terms of Service | Stall Wise",
        "description": "The terms that govern selling and buying on Stall Wise.",
    },
    "privacy": {
        "title": "Privacy Policy | Stall Wise",
        "description": "How Stall Wise collects, uses and protects your data.",
    },
    "register": {
        "title": "Start Selling Online Free | Open Your Stall Wise Shop",
        "description": (
            "Create your online store in minutes. List products, share your link and "
            "receive payments directly in your bank account."
        ),
    },
    "shops": {
        "title": "Browse Shops on Stall Wise | Independent Indian Sellers",
        "description": (
            "Discover independent shops on Stall Wise — handmade goods, small-batch food, "
            "crafts and more. Pay the seller directly by UPI, card or cash on delivery."
        ),
    },
    "sell-online": {
        "title": "How to Sell Online in India | Start a Shop on Stall Wise",
        "description": (
            "A practical guide to selling online in India: set up a storefront, accept UPI, "
            "cards and cash on delivery, and get paid straight into your bank account."
        ),
    },
}


def _esc(v: Optional[str]) -> str:
    return html.escape(str(v or ""), quote=True)


def _clamp(text: Optional[str], limit: int = DESC_MAX) -> str:
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    return t[: limit - 1].rsplit(" ", 1)[0] + "…"


def absolute_media(path: Optional[str]) -> Optional[str]:
    """Turn a stored image key into an absolute, crawlable URL."""
    if not path:
        return None
    p = str(path)
    if p.startswith("http://") or p.startswith("https://"):
        return p
    if p.startswith("/"):
        return f"{SITE_URL}{p}"
    return f"{SITE_URL}/api/files/{p}"


def is_noindex(route: str) -> bool:
    r = (route or "").lstrip("/")
    return any(r == p.rstrip("/") or r.startswith(p) for p in NOINDEX_PREFIXES)


def build_head(*, title: str, description: str, canonical: str,
               image: Optional[str] = None, noindex: bool = False,
               og_type: str = "website", jsonld: Optional[str] = None) -> str:
    img = image or DEFAULT_OG_IMAGE
    robots = "noindex, nofollow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1"
    parts = [
        f"<title>{_esc(title)}</title>",
        f'<meta name="description" content="{_esc(description)}" />',
        f'<meta name="robots" content="{robots}" />',
        f'<link rel="canonical" href="{_esc(canonical)}" />',
        f'<meta property="og:type" content="{_esc(og_type)}" />',
        f'<meta property="og:site_name" content="{_esc(SITE_NAME)}" />',
        f'<meta property="og:title" content="{_esc(title)}" />',
        f'<meta property="og:description" content="{_esc(description)}" />',
        f'<meta property="og:url" content="{_esc(canonical)}" />',
        '<meta property="og:locale" content="en_IN" />',
        f'<meta name="twitter:card" content="{"summary_large_image" if img else "summary"}" />',
        f'<meta name="twitter:title" content="{_esc(title)}" />',
        f'<meta name="twitter:description" content="{_esc(description)}" />',
    ]
    if img:
        parts.append(f'<meta property="og:image" content="{_esc(img)}" />')
        parts.append(f'<meta name="twitter:image" content="{_esc(img)}" />')
    if jsonld:
        parts.append(f'<script type="application/ld+json">{jsonld}</script>')
    return "\n    ".join(parts)


def inject(base_html: str, head_block: str) -> str:
    out = base_html
    for pattern in _OWNED:
        out = pattern.sub("", out)
    # Collapse the blank lines the removals leave behind.
    out = re.sub(r"\n\s*\n(\s*\n)+", "\n\n", out)
    return out.replace("</head>", f"    {head_block}\n</head>", 1)


def store_jsonld(store: dict, seller: dict, products: Iterable[dict]) -> str:
    """Store + product offers, so a shop can win a rich result."""
    import json

    slug = store.get("slug")
    url = f"{SITE_URL}/{slug}"
    offers = []
    for p in list(products)[:50]:
        offers.append({
            "@type": "Offer",
            "url": url,
            "price": f"{float(p.get('price') or 0):.2f}",
            "priceCurrency": "INR",
            "availability": (
                "https://schema.org/OutOfStock" if p.get("stock") == 0 else "https://schema.org/InStock"
            ),
            "itemOffered": {
                "@type": "Product",
                "name": p.get("title"),
                "description": _clamp(p.get("description") or p.get("title"), 300),
                **({"image": absolute_media(p.get("image"))} if p.get("image") else {}),
            },
        })

    node = {
        "@context": "https://schema.org",
        "@type": "Store",
        "@id": f"{url}#store",
        "name": store.get("name"),
        "url": url,
        "description": _clamp(store.get("bio") or f"Shop from {store.get('name')} on {SITE_NAME}.", 300),
        "currenciesAccepted": "INR",
        "parentOrganization": {"@type": "Organization", "name": SITE_NAME, "url": f"{SITE_URL}/"},
    }
    logo = absolute_media(seller.get("avatar") if seller else None)
    if logo:
        node["image"] = logo
        node["logo"] = logo
    if offers:
        node["makesOffer"] = offers
    return json.dumps(node, separators=(",", ":"))


def store_meta(store: dict, seller: dict, products: list) -> dict:
    name = store.get("name") or "Shop"
    slug = store.get("slug")
    bio = store.get("bio")
    count = len(products or [])
    if bio:
        description = _clamp(bio)
    else:
        noun = f"{count} product{'s' if count != 1 else ''}" if count else "products"
        description = _clamp(
            f"Shop {noun} from {name} on {SITE_NAME}. Pay securely by UPI, card or "
            f"cash on delivery — your money goes straight to the seller."
        )
    return {
        "title": f"{name} — Shop Online | {SITE_NAME}",
        "description": description,
        "canonical": f"{SITE_URL}/{slug}",
        "image": absolute_media((seller or {}).get("avatar"))
        or absolute_media((products[0] or {}).get("image") if products else None),
        "og_type": "website",
        "jsonld": store_jsonld(store, seller, products or []),
    }


def product_jsonld(store: dict, seller: dict, product: dict) -> str:
    """Product + Offer + BreadcrumbList — what a long-tail product query needs
    to earn a rich result."""
    import json

    store_url = f"{SITE_URL}/{store.get('slug')}"
    url = f"{store_url}/{product.get('slug')}"
    images = [absolute_media(i) for i in (product.get("images") or [])]
    images = [i for i in images if i]
    in_stock = product.get("stock") != 0

    product_node = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"{url}#product",
        "name": product.get("title"),
        "description": _clamp(product.get("description") or product.get("title"), 500),
        "url": url,
        "brand": {"@type": "Brand", "name": store.get("name")},
        "offers": {
            "@type": "Offer",
            "url": url,
            "price": f"{float(product.get('price') or 0):.2f}",
            "priceCurrency": "INR",
            "availability": (
                "https://schema.org/InStock" if in_stock else "https://schema.org/OutOfStock"
            ),
            "seller": {"@type": "Organization", "name": store.get("name"), "url": store_url},
        },
    }
    if images:
        product_node["image"] = images

    breadcrumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": store.get("name"), "item": store_url},
            {"@type": "ListItem", "position": 3, "name": product.get("title"), "item": url},
        ],
    }
    return json.dumps([product_node, breadcrumbs], separators=(",", ":"))


def product_meta(store: dict, seller: dict, product: dict) -> dict:
    name = product.get("title") or "Product"
    store_name = store.get("name") or SITE_NAME
    price = float(product.get("price") or 0)
    desc = product.get("description")
    if desc:
        description = _clamp(desc)
    else:
        cod = "cash on delivery" if "cod" in (product.get("paymentMethods") or []) else "UPI, card or netbanking"
        description = _clamp(
            f"Buy {name} from {store_name} for ₹{price:,.0f} on {SITE_NAME}. "
            f"Pay by {cod} — your money goes straight to the seller."
        )
    images = product.get("images") or ([product["image"]] if product.get("image") else [])
    return {
        "title": f"{name} — ₹{price:,.0f} | {store_name}",
        "description": description,
        "canonical": f"{SITE_URL}/{store.get('slug')}/{product.get('slug')}",
        "image": absolute_media(images[0] if images else None)
        or absolute_media((seller or {}).get("avatar")),
        "og_type": "product",
        "jsonld": product_jsonld(store, seller, product),
    }


def directory_meta(count: int = 0) -> dict:
    return {
        "title": f"Browse Shops on {SITE_NAME} | Independent Indian Sellers",
        "description": _clamp(
            f"Discover {count or ''} independent shops on {SITE_NAME} — handmade goods, "
            f"small-batch food, crafts and more. Pay the seller directly by UPI, card or "
            f"cash on delivery.".replace("  ", " ")
        ),
        "canonical": f"{SITE_URL}/shops",
        "noindex": False,
    }


def static_meta(route: str) -> dict:
    r = (route or "").strip("/")
    page = STATIC_PAGES.get(r)
    canonical = f"{SITE_URL}/{r}" if r else f"{SITE_URL}/"
    if page:
        return {
            "title": page["title"],
            "description": page["description"],
            "canonical": canonical,
            "noindex": False,
        }
    return {
        "title": STATIC_PAGES[""]["title"],
        "description": STATIC_PAGES[""]["description"],
        "canonical": canonical,
        "noindex": is_noindex(r),
    }


def robots_txt() -> str:
    disallow = "\n".join(f"Disallow: /{p}" for p in NOINDEX_PREFIXES)
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"{disallow}\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def sitemap_xml(stores: Iterable[dict], products: Iterable[dict] = ()) -> str:
    rows = [
        ("", "daily", "1.0"),
        ("shops", "daily", "0.9"),
        ("register", "monthly", "0.9"),
        ("sell-online", "monthly", "0.8"),
        ("about", "monthly", "0.7"),
        ("contact", "monthly", "0.6"),
        ("terms", "yearly", "0.3"),
        ("privacy", "yearly", "0.3"),
    ]
    urls = [
        f"  <url><loc>{SITE_URL}/{path}</loc>"
        f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
        for path, freq, prio in rows
    ]
    for s in stores:
        slug = _esc(s.get("slug"))
        created = s.get("created_at")
        lastmod = f"<lastmod>{_esc(str(created)[:10])}</lastmod>" if created else ""
        urls.append(
            f"  <url><loc>{SITE_URL}/{slug}</loc>{lastmod}"
            f"<changefreq>daily</changefreq><priority>0.8</priority></url>"
        )
    for p in products:
        if not p.get("slug") or not p.get("store_slug"):
            continue
        created = p.get("created_at")
        lastmod = f"<lastmod>{_esc(str(created)[:10])}</lastmod>" if created else ""
        urls.append(
            f"  <url><loc>{SITE_URL}/{_esc(p['store_slug'])}/{_esc(p['slug'])}</loc>{lastmod}"
            f"<changefreq>weekly</changefreq><priority>0.7</priority></url>"
        )
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )

# Marketo — PRD

## Original Problem Statement
Multi-vendor marketplace MVP. Each seller gets a shop at `/{storeSlug}`, lists products, shares the link with buyers. Focus: backend logic + data models + minimal functional UI (styling handled separately). No commission, no escrow — money goes straight to sellers via their own Razorpay. Revenue only from seller premium (ad-free) subscriptions.

## User Choices
- Auth: email+password JWT + Google sign-in + forgot/reset password.
- Payment: Razorpay only. Sellers enter own Key ID + Secret; secret AES-256-GCM encrypted at rest, never exposed. Backend creates order server-side; signed webhook flips to paid.
- Email: Resend (Emergent-managed) — new-order email to seller, OTP to buyer, password reset.
- OTP: emailed to buyer at ship + shown on buyer order page.
- Subscription tiers: Paid = **Marketo Pro**, Free = **Community**.
- Name note: "Marketo" kept per user; alternates suggested (Storefy, Stallo, Vendra).

## Architecture
- Backend: FastAPI (`/app/backend/server.py`, `security.py`, `email_service.py`), MongoDB (motor). UUID string ids, `{"_id":0}` projections.
- Frontend: React (CRA + react-router v7), cookie auth (withCredentials). Pages under `/app/frontend/src/pages`.
- Auth: JWT access/refresh httpOnly cookies + Emergent Google session_token; unified `get_current_user`.

## Data Models
- User: user_id, email, name, password_hash?, role, authProvider, subscriptionStatus, picture.
- Store: store_id, sellerId, name, slug (unique, lowercase-alnum-hyphen), acceptanceWindowMinutes.
- Product: product_id, sellerId, storeSlug, title, description, price, stock?, optionGroups[{name, options[{label,priceDelta,stock}]}], active, image.
- Order: order_id, buyerName, buyerEmail, sellerId, storeSlug, items[{productId,title,optionSelections,quantity,unitPrice}], amount, status, otpCodeHash, otpEnc, otpGeneratedAt, otpAttempts, otpLocked, deliveryConfirmedAt, acceptanceWindowMinutes, windowExpiresAt, disputeRaised, disputeReason, razorpayOrderId, razorpayKeyId, mockPayment.
- seller_gateways: sellerId, key_id, key_secret_enc, webhook_secret_enc.

## Implemented (2026-08-27)
- Shop routing `/{storeSlug}` public page with products + ads flag by subscription.
- Full order state machine: placed→paid→shipped→delivered_pending_otp→delivered_confirmed→completed/disputed. Server-side timestamp window; auto-complete on read; no refund after window.
- OTP: issue at ship (emailed + shown to buyer), verify on confirm, 5-attempt lockout, expiry; seller view never exposes otp/hash.
- Per-seller Razorpay connect (AES-256-GCM), server-side order create, signed webhook, MOCK simulate-payment for testing.
- Flexible product option groups with price deltas.
- Seller dashboard: store settings, gateway, products CRUD, orders list+filter, order detail (OTP entry, live countdown, dispute), subscription toggle.
- Emails: new-order (seller), OTP (buyer), password reset — via Resend gate.
- Auth: register/login/logout/me/refresh/forgot/reset + Google.
- Verified: 9/9 backend pytest, 12/12 frontend E2E, 100% pass.

## Implemented (2026-08-27, iteration 2)
- **Stock Control**: per-option and product-level stock decremented atomically-ish at order placement; sell-outs blocked with 409; shop UI shows stock counts, disables sold-out options, and shows "Sold out" on fully-depleted products.
- **Live Marketo Pro billing (Razorpay)**: real platform Razorpay wired (₹199/mo, ₹999/yr). Attempts auto-recurring Subscriptions (plan+subscription via API); the provided TEST account lacks the Subscriptions feature (Plans API 401), so it auto-falls back to a real one-time Razorpay Order that grants a Pro period (30/365 days) on payment, verified via `verify_payment_signature`. Ads gate on effective subscription status (with expiry auto-downgrade). Webhook handler `/api/webhooks/razorpay-subscription` ready for when Subscriptions is enabled.

## MOCKED / TEST-ONLY
- `/orders/{id}/simulate-payment` — mock order payment when a seller has no Razorpay connected.
- `/subscription/simulate` — TEST-ONLY helper to flip subscriptionStatus without a real charge. NOTE: currently only requires login; should be gated behind an env flag before real production launch so sellers can't self-activate Pro.

## Known MVP trade-offs (advisory, non-blocking)
- Stock check + decrement not wrapped in a Mongo transaction (rare concurrent-order race).
- server.py is large; could be split into routers.

## Backlog
- P1: Real platform Razorpay subscription plan + webhook (needs Marketo account keys).
- P1: Buyer accounts/login (currently guest via email link).
- P2: Full UI/UX design pass (separate tool), image uploads (object storage), push notifications, product stock decrement on order.

## 2026-06 — Marketing Landing Page (DONE)
- Rewrote `/app/frontend/src/pages/Landing.js` as a full marketing homepage (Swiss-brutalist design: Cabinet Grotesk + Satoshi, orange #FF4F00 accent, hard borders/shadows, CSS-only entrance animations).
- Sections: Hero (h1 + "Start Selling" CTA), How it works (3 steps w/ optimized Unsplash images, lazy-loaded), Why Marketo (0% commission / direct payments / free to start / own link), Premium teaser (Free ₹0 w/ ads, Pro ₹149/mo, Pro ₹999/yr), Social-proof placeholders (3 greyed stats + 3 greyed testimonial cards), "Visit a shop" slug form (preserved), Footer.
- New: `components/SiteFooter.js`, `components/StaticPage.js`, `lib/useDocumentMeta.js`, stub pages `About.js` / `Terms.js` / `Privacy.js` / `Contact.js`, routes added in `App.js` ABOVE the catch-all `/:storeSlug`.
- SEO: real title + meta description, OG/Twitter tags, canonical, per-page meta via `useDocumentMeta`, JSON-LD @graph (Organization, WebSite, Service w/ 3 offers, FAQPage) in `public/index.html`, per-stub-page JSON-LD (AboutPage/ContactPage/WebPage), `public/robots.txt`, `public/sitemap.xml`, `public/llms.txt` for AI search.
- Tested: testing agent iteration_3.json — 14/14 frontend checks passed, 100%, no issues. Note: the preview host serves its own /robots.txt, overriding the bundled file (will apply on real domain deploy).

### Backlog (unchanged)
- P1 Order pagination on seller dashboard
- P2 Low-stock alert emails
- P2 Gate simulate-subscription test helpers behind admin flag
- P2 Migrate Pro billing from one-time Orders API to Razorpay Subscriptions API

## 2026-06 — Auth UI/UX (DONE)
- New `components/AuthShell.js`: split-screen auth layout matching the landing page (black value-prop panel on lg+, brutalist bordered form card with hard shadow). Exports shared `AuthField`, `AuthSubmit`, `AuthAlert`.
- Restyled `Login.js`, `Register.js`, `ForgotPassword.js`, `ResetPassword.js`. All original data-testids preserved. Added: password show/hide toggles, submit busy states ("Logging in…"), styled inline error/success alerts, real Google "G" SVG button, autocomplete attributes, per-page SEO meta, Terms/Privacy consent line on register.
- Fixed pricing inconsistency: `MARKETO_PRO_MONTHLY_PRICE` in backend/.env was 199 while the landing page quotes ₹149 — now 149. Verified via GET /api/subscription -> plans.monthly = 149.
- Verified: all four auth pages render, invalid-login error state shows, real owner login redirects to /dashboard.

## 2026-06 — Seller Dashboard + Order Detail redesign (DONE)
- New `components/Kit.js`: shared `Panel`, `Field`, `Btn`, `StatusPill`, `Note` primitives in the Swiss-brutalist system.
- `pages/Dashboard.js` rewritten: sticky brand header with logout, h1 + intro, five bordered hard-shadow panels (Store settings w/ live shop link + Razorpay connection badge, Payment gateway, Products with dashed create-form + table, Orders with status filter and colour-coded StatusPills, Subscription with ₹149/mo and ₹999/yr plan cards + testing helpers demoted to small underlined links). All original data-testids preserved.
- `pages/OrderDetail.js` rewritten: header w/ back link, big order id, status pill, Summary panel (buyer/total/itemised list/window), Delivery panel (ship → out-for-delivery → OTP entry w/ attempts counter), large countdown for the dispute window, dispute callout.
- Bug fix: `OrderDetail.act()` now reloads in a `finally` block so the OTP attempts counter and lock flag stay in sync after a failed OTP.
- Cleaned leftover TEST_* seed products from the demo store.
- Tested: testing agent iteration_4.json — 12/12 scenarios passed incl. full order state machine (placed→paid→shipped→delivered_confirmed with OTP + live countdown), Razorpay connect/disconnect, product CRUD with option groups, subscription toggle, mobile 390px no overflow. Only finding was the OTP counter staleness, now fixed.

### Remaining unstyled pages
- `pages/Shop.js` (public shop page) and `pages/BuyerOrder.js` (buyer order tracking) are the last two pages still on the old plain layout.

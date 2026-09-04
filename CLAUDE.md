# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Stall Wise** (`stallwise.in`) — a direct-payout multi-vendor marketplace for Indian
sellers. Each seller gets a storefront at `/{storeSlug}`, lists products with variant
option groups, and shares the link. Buyers pay via Razorpay; the platform takes a 10%
commission (see caveat below) and, with Razorpay Route, splits the payout so the
seller's share settles to their own bank account. Delivery is confirmed with an
emailed OTP the buyer shows the seller on handover. Monetization: **Stall Wise Pro**
subscription (₹199/mo or ₹1499/yr) vs the **Free Plan**.

> `memory/PRD.md` is the original brief and is now **stale** — it says "Marketo",
> MongoDB, CRA, Resend, and 0% commission. None of that is current. Trust the code.

## Commands

All frontend commands run from the repo root; Python commands from `backend/`.

| Task | Command |
|---|---|
| Install frontend deps | `npm install` (npm is canonical — `bun.lock` is stale, ignore it) |
| Frontend dev server | `npm run dev` → http://localhost:3000, proxies `/api` → `127.0.0.1:8000` |
| Frontend production build | `npm run build` → outputs to `dist/` |
| Typecheck / "lint" | `npm run lint` (`tsc --noEmit` — there is no ESLint) |
| Install backend deps | `pip install -r backend/requirements.txt` |
| Backend dev server | `cd backend && python -m uvicorn server:app --reload --port 8000` |
| Backend tests | `cd backend && pytest` (see caveats) |
| Run one backend test | `cd backend && pytest tests/backend_test.py::test_login_owner -n 0` |

### Backend test caveats

- `backend/tests/` are **integration tests that hit a running server over HTTP**, not
  unit tests. `conftest.py` needs `REACT_APP_BACKEND_URL` set (it otherwise tries to
  read `/app/frontend/.env`, an Emergent-container path that does not exist locally).
  Start the backend, then `REACT_APP_BACKEND_URL=http://localhost:8000 pytest`.
- `pytest.ini` pins `-n 2 --dist loadscope` (pytest-xdist). Do **not** edit `addopts`.
  For serial runs use `-n 0`, never `-p no:xdist`.
- Fixtures reference seeded demo accounts whose credentials have drifted from the
  current `seed()` in `server.py` (`conftest.py` still uses old Marketo emails) — the
  `owner_session` fixture will fail until updated to match `ADMIN_EMAIL`.
- `backend/test_jwt.py` and `test_rzp.py` are throwaway scratch scripts, not pytest.

## Architecture

### Backend — `backend/server.py` (single ~1500-line file)

FastAPI app. All API routes are on an `APIRouter(prefix="/api")`; `/health` and the
SPA fallback are on the root app. Supporting modules:

- **`db.py`** — dual-engine data layer. Tries PostgreSQL (`asyncpg`) using
  `DATABASE_URL`/`POSTGRES_URL`/`SUPABASE_DB_URL`/etc.; **falls back to local WAL
  SQLite** (`backend/stallwise.db`, or `/data/stallwise.db` if `/data` exists) if PG
  is unconfigured or unreachable — and also falls back per-query if a live PG call
  throws. **Write all SQL in PostgreSQL dialect** (`$1` placeholders, `::jsonb`,
  `ON CONFLICT`); `_pg_to_sqlite()` rewrites it at runtime for the SQLite path. JSON
  columns (`option_groups`, `address`, `items`) are stored as text in SQLite and
  auto-decoded in `_row_to_dict`. There are no migrations — SQLite schema lives in
  `_init_sqlite_schema()`; PG schema is assumed to exist / created in `init_db`.
- **`security.py`** — bcrypt passwords, HS256 JWT (`create_access_token` 180d /
  `create_refresh_token` 365d), AES-256-GCM for secrets at rest (`encrypt_secret` /
  `decrypt_secret`), 6-digit OTP (bcrypt-hashed), and an **in-memory** sliding-window
  rate limiter (`check_rate_limit` — not shared across workers/instances).
- **`email_service.py`** — transactional email via **Brevo REST API** (`api.brevo.com`).
  Auth OTP, buyer delivery OTP, new-order-to-seller, password reset. `backend/mailer.js`
  (nodemailer) is an alternate path bundled in the Docker image but not used by the
  Python code.
- **`route_service.py`** — Razorpay Route: onboards each seller as a Linked Account
  (sub-merchant). Falls back to a **mock linked account** when Route isn't enabled on
  the platform key, so onboarding works end-to-end regardless.
- **`storage.py`** — image uploads. Bytes go in the **`media` table**, not the
  container filesystem: Railway rebuilds that on every deploy and `uploads` is in
  `.dockerignore`, so photos written to disk were gone by the next release. Reads
  fall back to disk so anything already written there still serves. Served through
  `GET /api/files/{path}`, immutable for a year with an ETag derived from the path
  (every stored name ends in a fresh uuid, so the bytes never change). Note:
  internal names still say "marketo".
- **`ai_service.py`** — AI-written product descriptions for the seller's product
  editor. Talks to any **OpenAI-compatible** chat-completions endpoint via the
  `openai` SDK; defaults to `deepseek-ai/deepseek-v4-flash-0731` on NVIDIA NIM
  (`AI_BASE_URL` / `AI_MODEL` to change provider, `NVIDIA_API_KEY` or `AI_API_KEY`
  for the credential). Streaming, reasoning off (`AI_THINKING`) — the seller watches
  it fill a textarea. **The default model is text-only, so `AI_VISION` defaults to
  false and product photos are NOT sent**; the prompt then tells the model it cannot
  see the item and must not invent an appearance. Turn `AI_VISION=true` on only with
  a vision-capable `AI_MODEL`. **Optional by design:** with no key the module imports
  fine, `enabled()` returns False, `GET /api/ai/status` reports it, and the UI hides
  the button — nothing in it may raise at import time.
  `POST /api/ai/product-description` streams server-sent events
  (`{type: delta|done|error}`); because the response is already 200 when the model
  call can fail, upstream failures arrive as an `error` event, not an HTTP status.
  Only the seller's own uploaded image keys are ever read (`_own_upload_keys` in
  `server.py`), reasoning deltas are dropped, and seller text is wrapped in
  `<seller_input>` tags the system prompt tells the model to treat as data.
- **Entry chain:** `index.html` → `src/main.tsx` → `@/App`. The `@` alias resolves to
  **`frontend/src/`** (see `vite.config.ts`), so `@/App` is `frontend/src/App.js`.
  **Dead files to ignore:** `src/App.tsx` (stub returning `<div/>`), `src/index.css`,
  and `frontend/src/index.js` (an unused alternate entry with react-query).
- Source files are `.js` but contain JSX — `vite.config.ts` has a custom plugin +
  esbuild loader config to treat `frontend/src/**/*.js` as JSX. `components/ui/*` are
  shadcn components and use `.jsx`.
- **Routing** (`App.js`): public pages, `/login` `/register` etc., `<Protected>`
  dashboard routes, and a catch-all `/:storeSlug` → `Shop`. Auth state comes from
  `context/AuthContext` (`useAuth()`).
- **API client:** `lib/api.js` — a single axios instance (`withCredentials`) with
  interceptors that attach the stored bearer token and transparently retry once
  through `/api/auth/refresh` on a 401. Always import this, don't call `fetch`.
- `pages/Dashboard.js` is ~1900 lines and holds most seller-side UI (store settings,
  products, orders, Route onboarding, subscription) as sections within one file.
- **Design system:** `design_guidelines.json` — "Swiss Brutalist + High-Contrast",
  Cabinet Grotesk headings / Satoshi body (loaded from fontshare in `index.html`),
  accent `#FF4F00`. Shared primitives in `components/Kit.js`.

### Deployment

- **Railway** (`railway.json` + `Dockerfile`): single service. Multi-stage build —
  stage 1 builds the frontend to `dist/`, stage 2 is Python 3.11 running
  `uvicorn backend.server:app`. In production `server.py` mounts `dist/` and serves the
  SPA for all non-`/api` routes. Healthcheck: `/health`.
- **Vercel** (`vercel.json`): frontend-only static deploy of `dist/` with SPA rewrites
  — expects the backend hosted elsewhere (`VITE_BACKEND_URL` / `REACT_APP_BACKEND_URL`).

## Gotchas

- **The Razorpay SDK sets no timeout.** `Client.request` catches
  `requests.exceptions.Timeout` but never passes one, and it retries on top, so a
  slow gateway hangs the call indefinitely. Every Razorpay call runs inside
  `asyncio.to_thread`, so hung calls hold threads in the default executor —
  exhaust it and image serving and (on SQLite) database queries stall with it,
  which is how one slow payment request stops the origin answering and Cloudflare
  reports 520. Always build clients through `route_service.razorpay_client()`,
  never `razorpay.Client()` directly; a test asserts this.
- **`/api/auth/google/session` was an authentication bypass** and has been
  removed. It took a `session_id`, asked `demobackend.emergentagent.com` (dead
  Emergent scaffolding) whose it was, and logged in as whatever email came back,
  creating the account if absent. Nothing in the UI ever offered Google sign-in.
  Do not reinstate an identity provider you do not control.
- **`DEV_OTP_ECHO=true` returns login OTPs in API responses** — a complete
  authentication bypass on a public deploy. `/health` now reports
  `status: "insecure"` when it is set. Never set it in Railway.
- **Shop settings must be applied, not just stored.** Delivery charges were
  saved on the store row and shown in Settings for a while without `checkout()`
  ever reading them, so buyers were never billed. `delivery_for()` is the single
  place that decides a delivery charge.
- **Postgres was never actually exercised.** Three separate defects meant a
  Postgres deployment silently failed and fell back to SQLite: (1) there was no
  `CREATE TABLE` for Postgres at all — `_init_sqlite_schema` is SQLite-only and
  `_pg_migrate` only ran ALTER/CREATE INDEX, so a fresh database had no tables;
  (2) `_pg_to_sqlite` JSON-encoded list/dict parameters on the SQLite path only,
  so every write touching `option_groups`/`images`/`payment_methods`/`address`/
  `items` raised `DataError: expected str, got list` on Postgres; (3) each of
  `fetch_one`/`fetch_all`/`fetch_val`/`execute` caught *any* Postgres error and
  silently re-ran the query against SQLite, so a failed INSERT landed in a
  different database than the next SELECT — the row was invisible immediately
  and gone at restart. All three are fixed: `_PG_SCHEMA`, `encode_args()` on both
  paths, and the per-query fallback now re-raises. **Run the suite against
  Postgres** (`STALLWISE_TEST_PG=postgresql://... pytest`) — CI does.
- **Never commit a `.db` file.** `backend/stallwise.db` was tracked in git, so
  `COPY . .` baked it into the Docker image; on a restart the image's copy was
  restored over live data. `*.db` is now in both `.gitignore` and `.dockerignore`
  (the latter needs the `**/*.db` form — Docker patterns are path-relative).
  `db.ephemeral_storage_warning()` reports when writes aren't landing anywhere
  durable — including a configured-but-unreachable Postgres — and `/health`
  surfaces it alongside `missingConfig`.
- **Streaming endpoints must not be buffered.** `/api/ai/product-description` sets
  `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no`. A proxy that
  buffers turns the live draft into one silent pause followed by a wall of text.
- **Live Razorpay platform keys and a Brevo API key are hardcoded as fallbacks** in
  `server.py`, `route_service.py`, and `email_service.py` (env vars override them).
  Treat these as real secrets; don't echo them into logs, commits, or new files.
- `COMMISSION_RATE_FREE` and `COMMISSION_RATE_PRO` in `server.py` are **both 0.10**;
  Pro buys an ad-free storefront and a badge, not a lower rate, and the marketing copy
  says so. `/api/subscription` used to hardcode `0.00` for active subs while checkout
  took 10% — two endpoints quoting different rates, neither matching the money. Both
  now read those constants; a test buys something and compares the quoted rate against
  the split actually sent to Razorpay. Keep it that way.
- **There is one way a seller gets paid: the bank-details form.** It creates a
  Razorpay Route linked account that `checkout()` attaches its `transfers` block to.
  A second path once existed — sellers could POST their own Razorpay key and secret
  to `/api/seller/razorpay`, which stored the secret, reported `razorpayConnected`,
  and was read by no checkout at all. Removed, along with the `seller_gateways`
  table (dropped on boot via `db._DROPPED_TABLES`). Don't reintroduce a payment
  credential store nothing spends.
- **Never take an online payment that cannot be forwarded.** Checkout used to retry
  without the transfer when Razorpay rejected it, so the buyer paid, the order
  completed, and the whole amount stayed in the platform account with the seller
  unpaid and only a log warning. Both that case and "seller has no linked account"
  now refuse the payment; COD is unaffected. `_payouts_live()` is the single gate,
  keyed off the Route product's settlement state — the linked account sits at
  `created` long after transfers work, so account status is not the signal.
- **Onboarding is resumable on purpose.** Razorpay enforces a unique `reference_id`
  per linked account, so if step 1 lands and step 2 or 3 fails, re-creating locks the
  seller out for ever. `RouteError` carries the `account_id` and the row is saved on
  the failure path. Razorpay's own 4xx is returned to the seller as a 400 — a 5xx gets
  replaced by Cloudflare's error page and they never see the reason.
- **Stock is taken at checkout and must be given back.** Nothing released it until
  `release_abandoned_checkouts()` existed, so every closed payment window permanently
  removed a unit from the shop. A late payment re-reserves rather than losing the sale.
- **Emails follow the money, not the form.** `_notify_new_order` fires at placement
  for COD and at payment for online. `_mark_order_paid` is the single paid transition
  for both the browser callback and the webhook, compare-and-swapped on `paid_at` so
  only one of them sends the receipt. Buyer links are `/order/<id>?email=...` (public);
  `/orders/<id>` is the seller console and needs a login.
- **AI is off unless switched on.** `AI_ENABLED` for the description writer,
  `AI_ASSISTANT_ENABLED` as well for the shop assistant. A key in the environment is
  not consent. The assistant proposes; it never writes — `/api/ai/assistant/apply`
  re-checks ownership and bounds server-side.
- The repo has an Emergent test-agent protocol block at the top of `test_result.md`
  ("DO NOT EDIT OR REMOVE") — historical, from the platform this was built on.
- `.emergent/`, `metadata.json`, `firebase-applet-config.json`, `assets/.aistudio/`
  are AI-Studio/Emergent scaffolding, not part of the running app.

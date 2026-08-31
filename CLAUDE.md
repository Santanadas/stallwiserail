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
- **`storage.py`** — image uploads to the local filesystem (`backend/uploads/`), served
  back through `GET /api/files/{path}`. Note: internal names still say "marketo".

**Auth flow:** `get_current_user` accepts a bearer token, `access_token` cookie, or
Emergent Google `session_token` cookie, resolved by `_resolve_user`. Login and
register are **two-step**: the endpoint returns `{pendingOtp, email, otpId}` and the
client must call `/api/auth/verify-otp` before a session is issued. Successful auth
sets httpOnly cookies **and** returns `token` in the JSON body (the SPA also persists
it in `localStorage`/`sessionStorage`).

**Order lifecycle:** `placed` → `paid` (Razorpay webhook `/api/webhooks/razorpay`, or
`mock-pay`) → `shipped` (generates + emails delivery OTP) → `delivered` (seller enters
buyer's OTP) → `completed`.

### Frontend — `frontend/src/` (React 19 + Vite 6 + Tailwind v4)

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

- **Live Razorpay platform keys and a Brevo API key are hardcoded as fallbacks** in
  `server.py`, `route_service.py`, and `email_service.py` (env vars override them).
  Treat these as real secrets; don't echo them into logs, commits, or new files.
- `COMMISSION_RATE_FREE` and `COMMISSION_RATE_PRO` in `server.py` are **both 0.10**
  right now, but `/api/subscription` reports `commissionRate: 0.00` for active subs.
  UI copy about "0% commission for Pro" is aspirational, not what the checkout math does.
- The repo has an Emergent test-agent protocol block at the top of `test_result.md`
  ("DO NOT EDIT OR REMOVE") — historical, from the platform this was built on.
- `.emergent/`, `metadata.json`, `firebase-applet-config.json`, `assets/.aistudio/`
  are AI-Studio/Emergent scaffolding, not part of the running app.

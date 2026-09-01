import { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, X, ArrowUp, Check, Loader2, AlertTriangle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { askAssistant } from "@/lib/aiAssistant";
import { aiEnabled } from "@/lib/aiDescription";
import { inr } from "./Pieces";

/**
 * The shop assistant.
 *
 * It answers from the seller's own data and can propose changes — but a
 * proposal is inert until the seller presses Apply, and Apply posts to a
 * separate endpoint that re-checks ownership and bounds server-side. So this
 * component is free to render whatever the model returned: nothing here is
 * trusted, and nothing here can write.
 */

const FIELDS = {
  price: { label: "Price", fmt: inr },
  stock: { label: "Stock", fmt: (v) => `${v} left` },
  active: { label: "Shown in shop", fmt: (v) => (v ? "Yes" : "Hidden") },
  paymentMethods: {
    label: "Payment",
    fmt: (v) => (v || []).map((m) => (m === "cod" ? "Cash on delivery" : "Online")).join(" + "),
  },
  deliveryFee: { label: "Delivery charge", fmt: inr },
  freeDeliveryAbove: { label: "Free delivery above", fmt: inr },
  dispatchDays: { label: "Dispatch time", fmt: (v) => `${v} day${v === 1 ? "" : "s"}` },
};

const describe = (key, value) => {
  const f = FIELDS[key];
  if (!f) return `${key}: ${String(value)}`;
  return f.fmt(value);
};

const STARTERS = [
  "What needs my attention today?",
  "Which products are running low?",
  "How did this month compare to last?",
];

function ProposalCard({ proposal, state, onApply, onDismiss }) {
  const keys = Object.keys(proposal.changes || {});
  const applied = state === "applied";
  const failed = state === "failed";

  return (
    <div
      className={`mt-2 overflow-hidden rounded-xl border ${
        applied ? "border-emerald-200 bg-emerald-50/60" : failed ? "border-rose-200 bg-rose-50/60" : "border-neutral-200 bg-white"
      }`}
    >
      <div className="border-b border-neutral-100 px-3.5 py-2.5">
        <div className="text-[13px] font-bold text-[#0A0A0A]">{proposal.label}</div>
        {proposal.reason && (
          <div className="mt-0.5 text-[11px] font-medium leading-snug text-neutral-500">{proposal.reason}</div>
        )}
      </div>

      <dl className="px-3.5 py-2.5">
        {keys.map((k) => (
          <div key={k} className="flex items-baseline justify-between gap-3 py-1">
            <dt className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">
              {FIELDS[k]?.label || k}
            </dt>
            <dd className="flex items-baseline gap-1.5 text-[13px] font-semibold text-[#0A0A0A]">
              {proposal.before && k in proposal.before && (
                <span className="text-neutral-400 line-through">{describe(k, proposal.before[k])}</span>
              )}
              <span>{describe(k, proposal.changes[k])}</span>
            </dd>
          </div>
        ))}
      </dl>

      <div className="flex items-center gap-2 border-t border-neutral-100 px-3.5 py-2.5">
        {applied ? (
          <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-700">
            <Check className="h-3.5 w-3.5" /> Applied
          </span>
        ) : failed ? (
          <span className="flex items-center gap-1.5 text-xs font-bold text-rose-700">
            <AlertTriangle className="h-3.5 w-3.5" /> {proposal.error || "Couldn't apply that"}
          </span>
        ) : (
          <>
            <button
              type="button"
              onClick={onApply}
              disabled={state === "applying"}
              className="inline-flex min-h-[36px] items-center gap-1.5 rounded-[10px] bg-[#FF4F00] px-3.5 text-xs font-extrabold text-white transition-colors hover:bg-[#E04500] disabled:opacity-50"
            >
              {state === "applying" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              Apply
            </button>
            <button
              type="button"
              onClick={onDismiss}
              disabled={state === "applying"}
              className="min-h-[36px] rounded-[10px] px-3 text-xs font-bold text-neutral-500 transition-colors hover:bg-neutral-100"
            >
              Not now
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function Assistant({ onApplied }) {
  const [available, setAvailable] = useState(false);
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let alive = true;
    aiEnabled().then((on) => alive && setAvailable(on));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ block: "end" });
  }, [turns, open, busy]);

  useEffect(() => {
    if (!open) return undefined;
    const esc = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open]);

  const send = useCallback(async (text) => {
    const message = (text ?? draft).trim();
    if (!message || busy) return;
    setDraft("");
    setError("");
    setBusy(true);
    setStatus("Thinking");

    // Snapshot before appending, so the model sees the conversation as it was.
    const history = turns
      .filter((t) => t.role === "user" || t.role === "assistant")
      .slice(-12)
      .map((t) => ({ role: t.role, content: t.content }));
    setTurns((prev) => [...prev, { role: "user", content: message }]);

    const stop = new AbortController();
    abortRef.current = stop;
    try {
      const data = await askAssistant({ message, history }, {
        signal: stop.signal,
        onStatus: setStatus,
      });
      setTurns((prev) => [...prev, {
        role: "assistant",
        content: data.reply || "",
        proposals: (data.proposals || []).map((p) => ({ ...p, state: "open" })),
      }]);
    } catch (e) {
      if (e?.name !== "AbortError") {
        setError(e?.message || formatApiError(e) || "The assistant couldn't be reached.");
      }
    } finally {
      abortRef.current = null;
      setBusy(false);
      setStatus("");
      inputRef.current?.focus();
    }
  }, [draft, busy, turns]);

  const setProposalState = (turnIdx, propIdx, patch) =>
    setTurns((prev) => prev.map((t, i) => (i !== turnIdx ? t : {
      ...t,
      proposals: t.proposals.map((p, j) => (j !== propIdx ? p : { ...p, ...patch })),
    })));

  const apply = async (turnIdx, propIdx, proposal) => {
    setProposalState(turnIdx, propIdx, { state: "applying" });
    try {
      const { data } = await api.post("/ai/assistant/apply", {
        proposals: [{ kind: proposal.kind, productId: proposal.productId, changes: proposal.changes }],
      });
      if (data.applied?.length) {
        setProposalState(turnIdx, propIdx, { state: "applied" });
        onApplied?.();
      } else {
        setProposalState(turnIdx, propIdx, {
          state: "failed",
          error: data.failed?.[0]?.reason || "That change was rejected.",
        });
      }
    } catch (e) {
      setProposalState(turnIdx, propIdx, { state: "failed", error: formatApiError(e) });
    }
  };

  if (!available) return null;

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          data-testid="assistant-open"
          className="fixed bottom-5 right-5 z-30 flex min-h-[52px] items-center gap-2 rounded-full bg-[#0A0A0A] px-5 text-[13px] font-extrabold text-white shadow-lg transition-transform hover:scale-[1.03] active:scale-[0.98]"
        >
          <Sparkles className="h-4 w-4 text-[#FF7A3D]" />
          Ask
        </button>
      )}

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/20 lg:hidden"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <aside
            role="dialog"
            aria-label="Shop assistant"
            className="fixed inset-x-0 bottom-0 top-16 z-40 flex flex-col border-neutral-200 bg-white sm:inset-y-0 sm:left-auto sm:right-0 sm:w-[420px] sm:border-l sm:shadow-2xl"
          >
            <header className="flex items-center justify-between gap-3 border-b border-neutral-200 px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-[#0A0A0A]">
                  <Sparkles className="h-4 w-4 text-[#FF7A3D]" />
                </div>
                <div>
                  <div className="mk-head text-sm font-black tracking-tight text-[#0A0A0A]">Shop assistant</div>
                  <div className="text-[11px] font-medium text-neutral-400">Reads your shop. Asks before changing it.</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex h-10 w-10 items-center justify-center rounded-[10px] text-neutral-400 transition-colors hover:bg-neutral-100"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-4">
              {turns.length === 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-[13px] font-medium leading-relaxed text-neutral-500">
                    Ask about your orders, stock or sales — or tell it what to change and confirm before it happens.
                  </p>
                  {STARTERS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => send(s)}
                      className="rounded-xl border border-neutral-200 px-3.5 py-2.5 text-left text-[13px] font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex flex-col gap-3.5">
                {turns.map((t, i) =>
                  t.role === "user" ? (
                    <div key={i} className="self-end rounded-2xl rounded-br-md bg-[#0A0A0A] px-3.5 py-2.5 text-[13px] font-medium text-white sm:max-w-[85%]">
                      {t.content}
                    </div>
                  ) : (
                    <div key={i} className="sm:max-w-[92%]">
                      {t.content && (
                        <div className="whitespace-pre-wrap rounded-2xl rounded-bl-md bg-neutral-100 px-3.5 py-2.5 text-[13px] font-medium leading-relaxed text-[#0A0A0A]">
                          {t.content}
                        </div>
                      )}
                      {(t.proposals || []).map((p, j) => (
                        <ProposalCard
                          key={j}
                          proposal={p}
                          state={p.state}
                          onApply={() => apply(i, j, p)}
                          onDismiss={() => setProposalState(i, j, { state: "dismissed" })}
                        />
                      ))}
                    </div>
                  )
                )}
                {busy && (
                  <div className="flex items-center gap-2 text-[13px] font-medium text-neutral-400">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>{status || "Thinking"}…</span>
                    <button
                      type="button"
                      onClick={() => abortRef.current?.abort()}
                      className="font-bold text-neutral-500 underline underline-offset-2 hover:text-neutral-800"
                    >
                      Stop
                    </button>
                  </div>
                )}
              </div>
              {error && (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs font-semibold text-rose-700">
                  {error}
                </div>
              )}
              <div ref={endRef} />
            </div>

            <form
              className="flex items-end gap-2 border-t border-neutral-200 p-3"
              onSubmit={(e) => { e.preventDefault(); send(); }}
            >
              <textarea
                ref={inputRef}
                rows={1}
                value={draft}
                maxLength={2000}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
                }}
                placeholder="Ask about your shop…"
                className="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl border border-neutral-200 px-3.5 py-3 text-[13px] font-medium text-[#0A0A0A] outline-none transition-all placeholder:text-neutral-400 focus:border-[#FF4F00] focus:ring-2 focus:ring-[#FF4F00]/10"
              />
              <button
                type="submit"
                disabled={busy || !draft.trim()}
                aria-label="Send"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#FF4F00] text-white transition-colors hover:bg-[#E04500] disabled:opacity-40"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </form>
          </aside>
        </>
      )}
    </>
  );
}

import api, { API, formatApiError } from "@/lib/api";

/**
 * Client for the Claude-backed description writer.
 *
 * The endpoint streams server-sent events, and axios can't hand us a stream in
 * the browser — so this uses fetch directly and borrows axios only for the
 * token refresh, which is where that logic already lives.
 */

function authToken() {
  try {
    return (
      localStorage.getItem("stallwise_token") ||
      sessionStorage.getItem("stallwise_token") ||
      ""
    );
  } catch {
    return "";
  }
}

let statusPromise = null;

/** Resolves false when no ANTHROPIC_API_KEY is configured, so the UI can hide
 *  the button entirely rather than offering something that 503s. */
export function aiEnabled() {
  if (!statusPromise) {
    statusPromise = api
      .get("/ai/status")
      .then((r) => Boolean(r.data?.enabled))
      .catch(() => {
        // Don't cache a transient failure — let the next open try again.
        statusPromise = null;
        return false;
      });
  }
  return statusPromise;
}

async function readError(res) {
  try {
    const body = await res.json();
    if (body?.detail) return formatApiError(body.detail);
  } catch {
    /* not JSON */
  }
  if (res.status === 503) return "AI descriptions aren't switched on yet.";
  if (res.status === 429) return "You've used this hour's AI drafts. Try again shortly.";
  return "Couldn't reach the AI writer. Try again in a moment.";
}

/**
 * Streams a description, calling `onDelta(fullTextSoFar)` as it arrives.
 * Resolves with the finished text. Pass an AbortSignal to let the seller stop.
 */
export async function streamProductDescription(payload, { onDelta, signal } = {}) {
  const send = () => {
    const token = authToken();
    return fetch(`${API}/ai/product-description`, {
      method: "POST",
      credentials: "include",
      signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });
  };

  let res = await send();
  if (res.status === 401) {
    // A long-lived editor session can outlive the access token. axios owns the
    // refresh flow; use it, then retry once.
    try {
      await api.post("/auth/refresh");
      res = await send();
    } catch {
      /* fall through to the error below */
    }
  }
  if (!res.ok || !res.body) throw new Error(await readError(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let split;
      while ((split = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, split).trim();
        buffer = buffer.slice(split + 2);
        if (!frame.startsWith("data:")) continue;

        let event;
        try {
          event = JSON.parse(frame.slice(5).trim());
        } catch {
          continue;
        }
        if (event.type === "delta") {
          text += event.text || "";
          onDelta?.(text);
        } else if (event.type === "error") {
          // The response was already 200 when this failed, so the message
          // travels in the stream rather than in a status code.
          throw new Error(event.message || "The AI writer stopped unexpectedly.");
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }

  return text;
}

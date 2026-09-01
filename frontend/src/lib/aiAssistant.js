import api, { API, formatApiError } from "@/lib/api";

/**
 * Client for the shop assistant.
 *
 * The turn arrives as server-sent events, so the panel can report each step
 * instead of showing one spinner for what may be several model calls. axios
 * cannot hand us a stream in the browser, so this uses fetch and borrows axios
 * only for the token refresh, which is where that logic already lives.
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

async function readError(res) {
  try {
    const body = await res.json();
    if (body?.detail) return formatApiError(body.detail);
  } catch {
    /* not JSON */
  }
  if (res.status === 503) return "The shop assistant isn't switched on yet.";
  if (res.status === 429) return "You've used this hour's assistant messages. Try again shortly.";
  return "Couldn't reach the assistant. Try again in a moment.";
}

/**
 * Runs one turn. Calls `onStatus(text)` as the assistant works and resolves
 * with { reply, proposals, usedTools }. Pass an AbortSignal to let the seller
 * give up.
 */
export async function askAssistant(payload, { onStatus, signal } = {}) {
  const send = () => {
    const token = authToken();
    return fetch(`${API}/ai/assistant`, {
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
  let result = null;

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
        if (event.type === "status") onStatus?.(event.text || "");
        else if (event.type === "error") throw new Error(event.message);
        else if (event.type === "done") {
          result = {
            reply: event.reply || "",
            proposals: event.proposals || [],
            usedTools: event.usedTools || [],
          };
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }

  if (!result) throw new Error("The assistant stopped part-way through. Try again.");
  return result;
}

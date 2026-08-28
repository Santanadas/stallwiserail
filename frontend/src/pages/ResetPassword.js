import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useDocumentMeta({
    title: "Set a new password | Marketo",
    description: "Choose a new password for your Marketo seller account.",
    path: "/reset-password",
  });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      setMsg("Password reset. Redirecting to login…");
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell testId="reset-page" title="Set a new password" subtitle="Pick something at least 6 characters long.">
      {!token && <AuthAlert data-testid="reset-missing-token">Missing token. Use the link from your email.</AuthAlert>}
      <form onSubmit={submit} className={`space-y-5 ${token ? "" : "mt-5"}`}>
        <div className="relative">
          <AuthField
            label="New password"
            data-testid="reset-password"
            type={show ? "text" : "password"}
            autoComplete="new-password"
            placeholder="At least 6 characters"
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="button"
            data-testid="reset-toggle-password"
            aria-label={show ? "Hide password" : "Show password"}
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-[34px] p-1 text-[#525252] transition-colors hover:text-[#FF4F00]"
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {msg && <AuthAlert tone="success" data-testid="reset-msg">{msg}</AuthAlert>}
        {error && <AuthAlert data-testid="reset-error">{error}</AuthAlert>}
        <AuthSubmit data-testid="reset-submit" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Set new password"}
        </AuthSubmit>
      </form>
      <p className="mt-6 border-t border-[#E5E5E5] pt-5 text-sm">
        <Link to="/login" data-testid="back-to-login" className="font-bold transition-colors hover:text-[#FF4F00]">
          ← Back to login
        </Link>
      </p>
    </AuthShell>
  );
}

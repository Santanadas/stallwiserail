import { useState } from "react";
import { Link } from "react-router-dom";
import { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const { resetPassword } = useAuth();

  useDocumentMeta({
    title: "Reset your password | Marketo",
    description: "Request a password reset link for your Marketo seller account.",
    path: "/forgot-password",
  });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setBusy(true);
    try {
      const res = await resetPassword(email);
      setMsg(res.message || "If that email exists, a reset link was sent.");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      testId="forgot-page"
      title="Forgot password"
      subtitle="Enter your email and we'll send a link to set a new password."
    >
      <form onSubmit={submit} className="space-y-5">
        <AuthField
          label="Email"
          data-testid="forgot-email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        {msg && <AuthAlert tone="success" data-testid="forgot-msg">{msg}</AuthAlert>}
        {error && <AuthAlert data-testid="forgot-error">{error}</AuthAlert>}
        <AuthSubmit data-testid="forgot-submit" type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send reset link"}
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

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { loginWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  useDocumentMeta({
    title: "Seller Login | Stall Wise",
    description: "Log in to your Stall Wise seller dashboard to manage products, orders and payouts.",
    path: "/login",
  });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const userData = await loginWithEmail(email, password);
      if (userData?.emailVerified === false) {
        navigate("/verify-email");
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  const googleLogin = async () => {
    setError("");
    setBusy(true);
    try {
      await loginWithGoogle();
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Failed to sign in with Google");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell testId="login-page" title="Welcome back" subtitle="Log in to manage your shop, orders and deliveries.">
      <form onSubmit={submit} className="space-y-5">
        <AuthField
          label="Email"
          data-testid="login-email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <div className="relative">
          <AuthField
            label="Password"
            data-testid="login-password"
            type={show ? "text" : "password"}
            autoComplete="current-password"
            placeholder="Your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="button"
            data-testid="login-toggle-password"
            aria-label={show ? "Hide password" : "Show password"}
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-[34px] p-1 text-[#525252] transition-colors hover:text-[#FF4F00]"
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {error && <AuthAlert data-testid="login-error">{error}</AuthAlert>}
        <AuthSubmit data-testid="login-submit" type="submit" disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </AuthSubmit>
      </form>

      <div className="my-6 flex items-center gap-4">
        <span className="h-px flex-1 bg-[#E5E5E5]" />
        <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">or</span>
        <span className="h-px flex-1 bg-[#E5E5E5]" />
      </div>

      <button
        type="button"
        data-testid="google-login-btn"
        onClick={googleLogin}
        className="flex w-full items-center justify-center gap-3 border-2 border-[#0A0A0A] bg-white px-6 py-3.5 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M23.5 12.3c0-.9-.1-1.5-.2-2.2H12v4.2h6.6c-.1 1.1-.8 2.7-2.4 3.8l3.7 2.8c2.2-2 3.6-5 3.6-8.6z" />
          <path fill="#34A853" d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.7-2.8c-1 .7-2.4 1.2-4.2 1.2-3.2 0-6-2.1-7-5L1.2 17c2 3.9 6 7 10.8 7z" />
          <path fill="#FBBC05" d="M5 14.5c-.3-.8-.4-1.6-.4-2.5s.2-1.7.4-2.5L1.2 6.6C.4 8.2 0 10 0 12s.4 3.8 1.2 5.4L5 14.5z" />
          <path fill="#EA4335" d="M12 4.7c2.3 0 3.8 1 4.7 1.8l3.4-3.3C18 1.2 15.2 0 12 0 7.2 0 3.2 3.1 1.2 6.6L5 9.5c1-2.9 3.8-4.8 7-4.8z" />
        </svg>
        Continue with Google
      </button>

      <div className="mt-6 flex flex-col gap-2 border-t border-[#E5E5E5] pt-5 text-sm sm:flex-row sm:items-center sm:justify-between">
        <Link to="/forgot-password" data-testid="forgot-link" className="text-[#525252] transition-colors hover:text-[#FF4F00]">
          Forgot password?
        </Link>
        <Link to="/register" data-testid="to-register" className="font-bold transition-colors hover:text-[#FF4F00]">
          Create a seller account →
        </Link>
      </div>
    </AuthShell>
  );
}

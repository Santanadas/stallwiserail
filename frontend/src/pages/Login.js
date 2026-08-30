import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import OtpVerify from "@/components/OtpVerify";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // OTP state
  const [otpPending, setOtpPending] = useState(false);
  const [otpId, setOtpId] = useState("");
  const [otpEmail, setOtpEmail] = useState("");

  const { loginWithEmail, setVerifiedUser } = useAuth();
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
      const result = await loginWithEmail(email, password);
      if (result.pendingOtp) {
        setOtpId(result.otpId);
        setOtpEmail(result.email);
        setOtpPending(true);
      } else {
        // Fallback if OTP is somehow not required
        setVerifiedUser(result);
        navigate("/dashboard");
      }
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleOtpVerified = (user) => {
    setVerifiedUser(user);
    navigate("/dashboard");
  };

  const handleOtpBack = () => {
    setOtpPending(false);
    setOtpId("");
    setOtpEmail("");
    setPassword("");
  };

  // OTP verification screen
  if (otpPending) {
    return (
      <AuthShell testId="login-otp-page" title="Verify your identity" subtitle="One more step to secure your account.">
        <OtpVerify
          email={otpEmail}
          otpId={otpId}
          onVerified={handleOtpVerified}
          onBack={handleOtpBack}
        />
      </AuthShell>
    );
  }

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

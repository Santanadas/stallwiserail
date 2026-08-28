import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Mail, CheckCircle, RefreshCw, KeyRound, ArrowRight } from "lucide-react";
import { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { auth, applyActionCode } from "@/lib/firebase";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [step, setStep] = useState("form"); // "form" | "verify"
  const [verificationCode, setVerificationCode] = useState("");
  const [checking, setChecking] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const { registerWithEmail, loginWithGoogle, sendVerificationEmail, checkEmailVerified } = useAuth();
  const navigate = useNavigate();
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  useDocumentMeta({
    title: step === "verify" ? "Verify your email | Marketo" : "Become a Seller | Marketo",
    description: "Create a free Marketo shop in minutes. 0% commission, payments straight to your own Razorpay account.",
    path: "/register",
  });

  // Cooldown timer for resend
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((c) => Math.max(0, c - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setBusy(true);
    try {
      await registerWithEmail(form);
      setStep("verify");
      setMsg("Verification email sent! Please check your inbox and verify your email to complete registration.");
      setCooldown(60);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleVerifyCode = async (e) => {
    if (e) e.preventDefault();
    if (!verificationCode.trim()) {
      setError("Please enter the verification code from your email link.");
      return;
    }
    setError("");
    setMsg("");
    setBusy(true);
    try {
      await applyActionCode(auth, verificationCode.trim());
      await checkEmailVerified();
      setMsg("Email verified successfully! Setting up your store...");
      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (err) {
      setError(err.message || "Invalid or expired verification code.");
    } finally {
      setBusy(false);
    }
  };

  const handleCheckStatus = async () => {
    setError("");
    setMsg("");
    setChecking(true);
    try {
      const isVerified = await checkEmailVerified();
      if (isVerified) {
        setMsg("Email verified! Redirecting to your dashboard...");
        setTimeout(() => {
          navigate("/dashboard");
        }, 1000);
      } else {
        setError("Email not verified yet. Please click the link sent to your inbox or paste the verification code below.");
      }
    } catch (err) {
      setError(err.message || "Could not check verification status.");
    } finally {
      setChecking(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    setError("");
    setMsg("");
    setBusy(true);
    try {
      const res = await sendVerificationEmail();
      setMsg(res.message || "New verification link sent to your email.");
      setCooldown(60);
    } catch (err) {
      setError(err.message || "Failed to resend verification email.");
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
      setError(err.message || "Failed to sign up with Google");
    } finally {
      setBusy(false);
    }
  };

  if (step === "verify") {
    return (
      <AuthShell
        testId="register-verify-step"
        title="Verify your email"
        subtitle={
          <>
            Almost done! We've sent a verification link to{" "}
            <span className="font-bold text-[#0A0A0A]">{form.email}</span>.
          </>
        }
      >
        <div className="space-y-5">
          <AuthAlert type="error" message={error} />
          <AuthAlert type="success" message={msg} />

          <div className="border-2 border-[#0A0A0A] bg-[#FAFAFA] p-4 text-sm leading-relaxed">
            <div className="flex items-start gap-3">
              <Mail className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4F00]" />
              <div>
                <p className="font-bold text-[#0A0A0A]">Verification Required</p>
                <p className="mt-1 text-xs text-[#525252]">
                  Click the link in the email we just sent you, or paste your verification code below to activate your account.
                </p>
              </div>
            </div>
          </div>

          <button
            type="button"
            data-testid="register-check-verified-btn"
            onClick={handleCheckStatus}
            disabled={checking || busy}
            className="flex w-full items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {checking ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" /> Checking status...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4" /> I've verified my email
              </>
            )}
          </button>

          <button
            type="button"
            data-testid="register-resend-btn"
            onClick={handleResend}
            disabled={busy || cooldown > 0}
            className="flex w-full items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-white px-4 py-3 text-sm font-bold text-[#0A0A0A] transition-transform hover:-translate-y-0.5 hover:bg-[#FAFAFA] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
            {cooldown > 0 ? `Resend email in ${cooldown}s` : "Resend verification email"}
          </button>

          <div className="border-t-2 border-[#0A0A0A] pt-4">
            <form onSubmit={handleVerifyCode} className="space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-[#525252]">
                <KeyRound className="h-3.5 w-3.5 text-[#FF4F00]" />
                <span>Enter verification code</span>
              </div>
              <div className="flex gap-2">
                <input
                  data-testid="register-verify-code-input"
                  type="text"
                  placeholder="Paste code from email link"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm font-mono outline-none focus:border-[#FF4F00]"
                />
                <button
                  type="submit"
                  data-testid="register-submit-code-btn"
                  disabled={busy || !verificationCode.trim()}
                  className="shrink-0 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Verify
                </button>
              </div>
            </form>
          </div>

          <div className="flex items-center justify-between pt-2 text-xs font-bold uppercase tracking-wider text-[#525252]">
            <button
              type="button"
              onClick={() => setStep("form")}
              className="text-[#0A0A0A] underline hover:text-[#FF4F00]"
            >
              ← Edit details
            </button>
            <Link to="/login" className="text-[#0A0A0A] hover:text-[#FF4F00]">
              Already verified? Log in
            </Link>
          </div>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      testId="register-page"
      title="Open your shop"
      subtitle="Free to start. No card required. You keep 100% of every sale."
    >
      <form onSubmit={submit} className="space-y-5">
        <AuthField
          label="Name"
          data-testid="register-name"
          autoComplete="name"
          placeholder="Your name or brand"
          value={form.name}
          onChange={upd("name")}
          required
        />
        <AuthField
          label="Email"
          data-testid="register-email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={upd("email")}
          required
        />
        <div className="relative">
          <AuthField
            label="Password"
            data-testid="register-password"
            type={show ? "text" : "password"}
            autoComplete="new-password"
            placeholder="At least 6 characters"
            minLength={6}
            value={form.password}
            onChange={upd("password")}
            required
          />
          <button
            type="button"
            data-testid="register-toggle-password"
            aria-label={show ? "Hide password" : "Show password"}
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-[34px] p-1 text-[#525252] transition-colors hover:text-[#FF4F00]"
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {error && <AuthAlert data-testid="register-error">{error}</AuthAlert>}
        <AuthSubmit data-testid="register-submit" type="submit" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </AuthSubmit>
      </form>

      <div className="my-6 flex items-center gap-4">
        <span className="h-px flex-1 bg-[#E5E5E5]" />
        <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">or</span>
        <span className="h-px flex-1 bg-[#E5E5E5]" />
      </div>

      <button
        type="button"
        data-testid="google-register-btn"
        onClick={googleLogin}
        className="flex w-full items-center justify-center gap-3 border-2 border-[#0A0A0A] bg-white px-6 py-3.5 text-sm font-bold transition-transform hover:-translate-y-0.5 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M23.5 12.3c0-.9-.1-1.5-.2-2.2H12v4.2h6.6c-.1 1.1-.8 2.7-2.4 3.8l3.7 2.8c2.2-2 3.6-5 3.6-8.6z" />
          <path fill="#34A853" d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.7-2.8c-1 .7-2.4 1.2-4.2 1.2-3.2 0-6-2.1-7-5L1.2 17c2 3.9 6 7 10.8 7z" />
          <path fill="#FBBC05" d="M5 14.5c-.3-.8-.4-1.6-.4-2.5s.2-1.7.4-2.5L1.2 6.6C.4 8.2 0 10 0 12s.4 3.8 1.2 5.4L5 14.5z" />
          <path fill="#EA4335" d="M12 4.7c2.3 0 3.8 1 4.7 1.8l3.4-3.3C18 1.2 15.2 0 12 0 7.2 0 3.2 3.1 1.2 6.6L5 9.5c1-2.9 3.8-4.8 7-4.8z" />
        </svg>
        Sign up with Google
      </button>

      <p className="mt-6 border-t border-[#E5E5E5] pt-5 text-sm text-[#525252]">
        Already a seller?{" "}
        <Link to="/login" data-testid="to-login" className="font-bold text-[#0A0A0A] transition-colors hover:text-[#FF4F00]">
          Log in
        </Link>
      </p>
      <p className="mt-3 text-xs leading-relaxed text-neutral-500">
        By creating an account you agree to our{" "}
        <Link to="/terms" className="underline hover:text-[#FF4F00]">Terms</Link> and{" "}
        <Link to="/privacy" className="underline hover:text-[#FF4F00]">Privacy Policy</Link>.
      </p>
    </AuthShell>
  );
}

import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Mail, CheckCircle, AlertCircle, ArrowRight, RefreshCw, KeyRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { auth, applyActionCode } from "@/lib/firebase";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const oobCode = searchParams.get("oobCode") || searchParams.get("code") || "";
  
  const { user, sendVerificationEmail, checkEmailVerified, logout } = useAuth();
  const navigate = useNavigate();

  const [code, setCode] = useState(oobCode);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [cooldown, setCooldown] = useState(0);

  useDocumentMeta({
    title: "Verify your email | Stall Wise",
    description: "Verify your email address to access your seller store on Stall Wise.",
  });

  // Auto-apply action code if present in URL
  useEffect(() => {
    if (oobCode) {
      handleApplyCode(oobCode);
    }
  }, [oobCode]);

  // Cooldown timer for resending email
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((c) => Math.max(0, c - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleApplyCode = async (actionCode) => {
    if (!actionCode || !actionCode.trim()) {
      setError("Please provide a valid verification code.");
      return;
    }
    setError("");
    setMsg("");
    setBusy(true);
    try {
      await applyActionCode(auth, actionCode.trim());
      await checkEmailVerified();
      setMsg("Email verified successfully! Redirecting to your dashboard...");
      setTimeout(() => {
        navigate("/dashboard");
      }, 1200);
    } catch (err) {
      setError(err.message || "Invalid or expired verification code.");
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    setError("");
    setMsg("");
    setBusy(true);
    try {
      const res = await sendVerificationEmail();
      setMsg(res.message || "Verification link sent to your email.");
      setCooldown(60);
    } catch (err) {
      setError(err.message || "Failed to resend verification email.");
    } finally {
      setBusy(false);
    }
  };

  const handleCheckStatus = async () => {
    setError("");
    setMsg("");
    setChecking(true);
    try {
      const verified = await checkEmailVerified();
      if (verified) {
        setMsg("Email verified! Redirecting to your dashboard...");
        setTimeout(() => {
          navigate("/dashboard");
        }, 1000);
      } else {
        setError("Email not verified yet. Please click the link sent to your email, or enter the code below.");
      }
    } catch (err) {
      setError(err.message || "Could not refresh verification status.");
    } finally {
      setChecking(false);
    }
  };

  return (
    <AuthShell
      title="Verify your email"
      subtitle={
        user?.email ? (
          <>
            We've sent a verification link to <span className="font-bold text-[#0A0A0A]">{user.email}</span>. Please verify to activate your seller account.
          </>
        ) : (
          "Please verify your email address to continue."
        )
      }
    >
      <div className="space-y-5">
        <AuthAlert type="error" message={error} />
        <AuthAlert type="success" message={msg} />

        <div className="border-2 border-[#0A0A0A] bg-[#FAFAFA] p-4 text-sm leading-relaxed">
          <div className="flex items-start gap-3">
            <Mail className="mt-0.5 h-5 w-5 shrink-0 text-[#FF4F00]" />
            <div>
              <p className="font-bold text-[#0A0A0A]">Verification link sent</p>
              <p className="mt-1 text-xs text-[#525252]">
                Check your inbox (and spam folder) for the verification email. Click the link inside, or enter your verification code below.
              </p>
            </div>
          </div>
        </div>

        {/* Check verification status button */}
        <button
          type="button"
          data-testid="verify-check-btn"
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

        {/* Resend link button */}
        <button
          type="button"
          data-testid="verify-resend-btn"
          onClick={handleResend}
          disabled={busy || cooldown > 0}
          className="flex w-full items-center justify-center gap-2 border-2 border-[#0A0A0A] bg-white px-4 py-3 text-sm font-bold text-[#0A0A0A] transition-transform hover:-translate-y-0.5 hover:bg-[#FAFAFA] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
          {cooldown > 0 ? `Resend link in ${cooldown}s` : "Resend verification email"}
        </button>

        {/* Manual Code / OTP verification option */}
        <div className="border-t-2 border-[#0A0A0A] pt-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleApplyCode(code);
            }}
            className="space-y-3"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-[#525252]">
              <KeyRound className="h-3.5 w-3.5 text-[#FF4F00]" />
              <span>Or enter verification code</span>
            </div>
            <div className="flex gap-2">
              <input
                data-testid="verification-code-input"
                type="text"
                placeholder="Paste code from email link"
                value={code || ""}
                onChange={(e) => setCode(e.target.value)}
                className="w-full border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm font-mono outline-none focus:border-[#FF4F00]"
              />
              <button
                type="submit"
                data-testid="verify-code-btn"
                disabled={busy || !code.trim()}
                className="shrink-0 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Verify
              </button>
            </div>
          </form>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between pt-2 text-xs font-bold uppercase tracking-wider text-[#525252]">
          <button
            type="button"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
            className="text-[#0A0A0A] underline hover:text-[#FF4F00]"
          >
            Sign in with another account
          </button>
          <Link to="/contact" className="text-[#0A0A0A] hover:text-[#FF4F00]">
            Need help?
          </Link>
        </div>
      </div>
    </AuthShell>
  );
}

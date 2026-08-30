import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import AuthShell, { AuthField, AuthSubmit, AuthAlert } from "@/components/AuthShell";
import OtpVerify from "@/components/OtpVerify";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // OTP state
  const [otpPending, setOtpPending] = useState(false);
  const [otpId, setOtpId] = useState("");
  const [otpEmail, setOtpEmail] = useState("");

  const { registerWithEmail, setVerifiedUser } = useAuth();
  const navigate = useNavigate();
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  useDocumentMeta({
    title: "Become a Seller | Stall Wise",
    description: "Create a free Stall Wise shop in minutes. 0% commission, payments straight to your own Razorpay account.",
    path: "/register",
  });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await registerWithEmail(form);
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
  };

  // OTP verification screen
  if (otpPending) {
    return (
      <AuthShell testId="register-otp-page" title="Verify your email" subtitle="Almost there! Confirm it's really you.">
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

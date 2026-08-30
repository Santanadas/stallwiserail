import { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "motion/react";
import { KeyRound, RefreshCw, Mail, ShieldCheck, AlertCircle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { AuthAlert } from "@/components/AuthShell";

const COOLDOWN_SECONDS = 60;
const CODE_LENGTH = 6;

/**
 * Shared OTP verification component for Login and Register pages.
 *
 * Props:
 *  - email: string          The email address the OTP was sent to
 *  - otpId: string           The initial OTP session ID
 *  - onVerified: (user) => void   Called with the user object on successful verification
 *  - onBack: () => void      Called when user wants to go back to credentials form
 */
export default function OtpVerify({ email, otpId: initialOtpId, onVerified, onBack }) {
  const [digits, setDigits] = useState(Array(CODE_LENGTH).fill(""));
  const [currentOtpId, setCurrentOtpId] = useState(initialOtpId);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cooldown, setCooldown] = useState(COOLDOWN_SECONDS);
  const inputRefs = useRef([]);

  // Cooldown timer for resend
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((c) => Math.max(0, c - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Auto-focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = useCallback(
    (index, value) => {
      // Only allow single digits
      const digit = value.replace(/\D/g, "").slice(-1);
      setDigits((prev) => {
        const next = [...prev];
        next[index] = digit;
        return next;
      });
      setError("");

      // Auto-advance to next input
      if (digit && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    },
    [],
  );

  const handleKeyDown = useCallback(
    (index, e) => {
      if (e.key === "Backspace" && !digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
      if (e.key === "ArrowLeft" && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
      if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    },
    [digits],
  );

  const handlePaste = useCallback((e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, CODE_LENGTH);
    if (!pasted) return;
    const newDigits = Array(CODE_LENGTH).fill("");
    for (let i = 0; i < pasted.length; i++) {
      newDigits[i] = pasted[i];
    }
    setDigits(newDigits);
    setError("");
    // Focus the next empty input or the last one
    const nextEmpty = newDigits.findIndex((d) => !d);
    inputRefs.current[nextEmpty >= 0 ? nextEmpty : CODE_LENGTH - 1]?.focus();
  }, []);

  // Submit OTP
  const verifyOtp = useCallback(
    async (code) => {
      if (!code || code.length !== CODE_LENGTH) return;
      setBusy(true);
      setError("");
      setSuccess("");
      try {
        const { data } = await api.post("/auth/verify-otp", {
          otp_id: currentOtpId,
          otp: code,
        });
        setSuccess("Verified! Redirecting…");
        onVerified(data);
      } catch (err) {
        setError(formatApiError(err.response?.data?.detail) || "Verification failed");
        // Clear digits on error for fresh input
        setDigits(Array(CODE_LENGTH).fill(""));
        inputRefs.current[0]?.focus();
      } finally {
        setBusy(false);
      }
    },
    [currentOtpId, onVerified],
  );

  // Auto-submit when all digits are filled
  useEffect(() => {
    const code = digits.join("");
    if (code.length === CODE_LENGTH && !busy) {
      verifyOtp(code);
    }
  }, [digits, busy, verifyOtp]);

  // Resend OTP
  const handleResend = async () => {
    if (cooldown > 0) return;
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/resend-otp", {
        otp_id: currentOtpId,
      });
      setCurrentOtpId(data.otpId);
      setCooldown(COOLDOWN_SECONDS);
      setDigits(Array(CODE_LENGTH).fill(""));
      setSuccess(data.message || "A new code has been sent.");
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || "Could not resend code");
    } finally {
      setBusy(false);
    }
  };

  const maskedEmail = email
    ? email.replace(/(.{2})(.*)(@.*)/, (_, a, b, c) => a + "•".repeat(Math.min(b.length, 6)) + c)
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-5"
      data-testid="otp-verify-form"
    >
      {/* Header */}
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="mx-auto mb-4 flex h-14 w-14 items-center justify-center border-2 border-[#0A0A0A] bg-[#FF4F00] shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]"
        >
          <ShieldCheck className="h-7 w-7 text-white" />
        </motion.div>
        <h2 className="mk-head text-xl font-black tracking-tight">Check your email</h2>
        <p className="mt-2 text-sm text-[#525252]">
          We sent a 6-digit code to{" "}
          <span className="font-bold text-[#0A0A0A]">{maskedEmail}</span>
        </p>
      </div>

      {/* OTP Digit Inputs */}
      <div className="flex justify-center gap-2 sm:gap-3" onPaste={handlePaste}>
        {digits.map((digit, i) => (
          <motion.input
            key={i}
            ref={(el) => (inputRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={1}
            value={digit}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            disabled={busy}
            data-testid={`otp-digit-${i}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`h-14 w-11 border-2 text-center text-xl font-black outline-none transition-all sm:h-16 sm:w-13 sm:text-2xl ${
              digit
                ? "border-[#FF4F00] bg-[#FFF4E0]"
                : "border-[#0A0A0A] bg-white"
            } focus:border-[#FF4F00] focus:shadow-[3px_3px_0px_0px_rgba(255,79,0,0.3)] disabled:opacity-50`}
          />
        ))}
      </div>

      {/* Status Messages */}
      {error && (
        <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}>
          <AuthAlert tone="error" data-testid="otp-error">
            {error}
          </AuthAlert>
        </motion.div>
      )}
      {success && (
        <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}>
          <AuthAlert tone="success" data-testid="otp-success">
            {success}
          </AuthAlert>
        </motion.div>
      )}

      {/* Loading indicator */}
      {busy && (
        <div className="flex items-center justify-center gap-2 text-sm font-medium text-[#525252]">
          <RefreshCw className="h-4 w-4 animate-spin text-[#FF4F00]" />
          Verifying…
        </div>
      )}

      {/* Resend and Back */}
      <div className="flex flex-col items-center gap-3 border-t-2 border-neutral-100 pt-5">
        <button
          type="button"
          onClick={handleResend}
          disabled={cooldown > 0 || busy}
          data-testid="otp-resend-btn"
          className="flex items-center gap-1.5 text-sm font-bold text-[#525252] transition-colors hover:text-[#FF4F00] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Mail className="h-4 w-4" />
          {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
        </button>

        {onBack && (
          <button
            type="button"
            onClick={onBack}
            data-testid="otp-back-btn"
            className="text-xs font-bold uppercase tracking-wider text-neutral-500 transition-colors hover:text-[#0A0A0A]"
          >
            ← Back to credentials
          </button>
        )}
      </div>
    </motion.div>
  );
}

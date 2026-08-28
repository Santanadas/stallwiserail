import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { Store, ArrowRight, Check, Loader2, Sparkles, CheckCircle2, AlertCircle, Camera, RefreshCw } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Field, Btn, Note } from "@/components/Kit";
import ImageUpload from "@/components/ImageUpload";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

const slugify = (s) =>
  s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

const STEPS = ["Welcome", "Store Name", "Profile Photo"];

function Progress({ step }) {
  return (
    <div className="mb-8 flex items-center gap-2" data-testid="onboarding-progress">
      {STEPS.map((label, i) => (
        <div key={label} className="flex flex-1 flex-col gap-2">
          <motion.div
            className={`h-2 w-full transition-all duration-500 ${
              i <= step ? "bg-[#FF4F00]" : "bg-neutral-200"
            }`}
            animate={{ scaleX: i <= step ? 1 : 0.98 }}
          />
          <span
            className={`text-[10px] font-bold uppercase tracking-widest transition-colors ${
              i <= step ? "text-[#0A0A0A]" : "text-neutral-400"
            }`}
          >
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Onboarding() {
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [ready, setReady] = useState(false);

  // Store name and slug
  const [handle, setHandle] = useState({ name: "", slug: "", bio: "" });
  const [slugDirty, setSlugDirty] = useState(false);
  const [handleErr, setHandleErr] = useState("");
  const [checkingSlug, setCheckingSlug] = useState(false);
  const [slugStatus, setSlugStatus] = useState(null); // null | 'available' | 'taken' | 'invalid'
  const [busy, setBusy] = useState(false);

  // Profile photo
  const [avatar, setAvatar] = useState(null);
  const debounceTimer = useRef(null);

  useDocumentMeta({
    title: "Welcome to Marketo | Set Up Your Store",
    description: "Create your free Marketo store in seconds.",
    path: "/onboarding",
  });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/stores/me");
        if (data) {
          // If store exists, check if user came here deliberately or redirect to dashboard
          const params = new URLSearchParams(window.location.search);
          if (!params.get("force")) {
            navigate("/dashboard", { replace: true });
            return;
          }
        }
      } catch {}
      if (user?.name) {
        const initialSlug = slugify(user.name);
        setHandle((h) => ({ ...h, name: user.name, slug: initialSlug }));
      }
      if (user?.avatar) setAvatar(user.avatar);
      setReady(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Real-time slug availability checker
  const checkAvailability = useCallback((slugToCheck) => {
    if (!slugToCheck || slugToCheck.length < 2) {
      setSlugStatus(null);
      return;
    }
    setCheckingSlug(true);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);

    debounceTimer.current = setTimeout(async () => {
      try {
        await api.get(`/shop/${slugToCheck}`);
        // If 200 OK, shop exists -> Taken
        setSlugStatus("taken");
      } catch (err) {
        if (err.response?.status === 404) {
          // 404 means available!
          setSlugStatus("available");
        } else {
          setSlugStatus(null);
        }
      } finally {
        setCheckingSlug(false);
      }
    }, 350);
  }, []);

  const onName = (e) => {
    const name = e.target.value;
    const newSlug = slugDirty ? handle.slug : slugify(name);
    setHandle((h) => ({ ...h, name, slug: newSlug }));
    setHandleErr("");
    if (!slugDirty) {
      checkAvailability(newSlug);
    }
  };

  const onSlug = (e) => {
    setSlugDirty(true);
    const newSlug = slugify(e.target.value);
    setHandle((h) => ({ ...h, slug: newSlug }));
    setHandleErr("");
    checkAvailability(newSlug);
  };

  const createShop = async () => {
    setHandleErr("");
    if (!handle.name.trim()) {
      setHandleErr("Please enter a name for your store.");
      return;
    }
    if (!handle.slug || handle.slug.length < 2) {
      setHandleErr("Please choose a valid store handle (at least 2 characters).");
      return;
    }
    if (slugStatus === "taken") {
      setHandleErr("This store handle is already taken. Please choose another one.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/stores", {
        name: handle.name,
        slug: handle.slug,
        bio: handle.bio || "",
        acceptanceWindowMinutes: 120,
      });
      // Move to PFP upload screen
      setStep(2);
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail);
      setHandleErr(msg);
      if (msg.toLowerCase().includes("taken")) {
        setSlugStatus("taken");
      }
    } finally {
      setBusy(false);
    }
  };

  const finish = useCallback(async () => {
    setBusy(true);
    try {
      await checkAuth();
    } finally {
      navigate("/dashboard", { replace: true });
    }
  }, [checkAuth, navigate]);

  if (!ready) {
    return (
      <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA]">
        <Loader2 className="h-8 w-8 animate-spin text-[#FF4F00]" />
      </div>
    );
  }

  // Animation configurations
  const screenVariants = {
    initial: { opacity: 0, y: 25, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } },
    exit: { opacity: 0, y: -20, scale: 0.98, transition: { duration: 0.3, ease: "easeInOut" } },
  };

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]" data-testid="onboarding-page">
      <header className="border-b-2 border-[#0A0A0A] bg-white shadow-sm">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-5 py-3.5">
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="mk-head text-lg font-black tracking-tighter"
          >
            MARKETO<span className="text-[#FF4F00]">.</span>
          </motion.div>
          {step > 0 && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={finish}
              data-testid="onboarding-skip-all"
              className="text-xs font-bold uppercase tracking-wider text-neutral-500 underline transition-colors hover:text-[#FF4F00]"
            >
              Skip to Profile →
            </motion.button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 py-10 md:py-16">
        <Progress step={step} />

        <AnimatePresence mode="wait">
          {/* SCREEN 1: Welcome Greeting */}
          {step === 0 && (
            <motion.div
              key="welcome-screen"
              variants={screenVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="text-center"
              data-testid="onboarding-welcome"
            >
              {/* Bouncing Store Icon */}
              <motion.div
                initial={{ scale: 0, rotate: -20 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{
                  type: "spring",
                  stiffness: 260,
                  damping: 18,
                  delay: 0.1,
                }}
                className="mx-auto flex h-24 w-24 items-center justify-center border-2 border-[#0A0A0A] bg-[#FF4F00] shadow-[8px_8px_0px_0px_rgba(10,10,10,1)]"
              >
                <Store className="h-12 w-12 text-white" />
              </motion.div>

              {/* Animated Headline */}
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25, duration: 0.5 }}
                className="mk-head mt-8 text-4xl font-black leading-[0.95] tracking-tighter sm:text-6xl"
              >
                Hi, Welcome to<br />
                Marketo<span className="text-[#FF4F00]">.</span>
              </motion.h1>

              {/* Subtitle */}
              <motion.p
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.5 }}
                className="mx-auto mt-5 max-w-md text-base leading-relaxed text-[#525252]"
              >
                Let's get your store launched in two quick steps: choose your store name and pick your profile photo.
              </motion.p>

              {/* Badges */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.45, duration: 0.4 }}
                className="mt-8 flex flex-wrap items-center justify-center gap-3 text-xs font-bold uppercase tracking-wider text-[#525252]"
              >
                <span className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-white px-3.5 py-1.5 shadow-[2px_2px_0px_0px_rgba(10,10,10,1)]">
                  <Sparkles className="h-4 w-4 text-[#FF4F00]" /> 0% Commission
                </span>
                <span className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-white px-3.5 py-1.5 shadow-[2px_2px_0px_0px_rgba(10,10,10,1)]">
                  <Check className="h-4 w-4 text-[#0B5227]" /> Direct Settlements
                </span>
              </motion.div>

              {/* Call to action button */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.55, duration: 0.4 }}
                className="mt-10"
              >
                <motion.button
                  whileHover={{ scale: 1.03, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  type="button"
                  data-testid="onboarding-start-btn"
                  onClick={() => setStep(1)}
                  className="inline-flex items-center gap-2 border-2 border-[#0A0A0A] bg-[#FF4F00] px-8 py-4 text-base font-bold text-white shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] hover:bg-[#E04500]"
                >
                  Let's set up your store <ArrowRight className="h-5 w-5" />
                </motion.button>
              </motion.div>
            </motion.div>
          )}

          {/* SCREEN 2: Store Name & Handle with Live Availability Check */}
          {step === 1 && (
            <motion.div
              key="handle-screen"
              variants={screenVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              data-testid="onboarding-handle"
            >
              <div className="border-2 border-[#0A0A0A] bg-white p-6 shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] sm:p-8">
                <div className="mb-2 inline-flex items-center gap-2 border border-[#0A0A0A] bg-[#FFF4E0] px-2.5 py-1 text-xs font-black uppercase tracking-wider text-[#FF4F00]">
                  Step 1 of 2
                </div>
                <h1 className="mk-head text-3xl font-black tracking-tighter sm:text-4xl">
                  What is your store name?
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-[#525252]">
                  Choose a memorable name for your store. We'll generate your custom shop link automatically.
                </p>

                <div className="mt-6 space-y-5">
                  <Field
                    label="Store Name"
                    data-testid="onboarding-shop-name"
                    placeholder="e.g. Studio Craft, Aisha's Ceramics"
                    value={handle.name}
                    onChange={onName}
                    autoFocus
                  />

                  <div>
                    <Field
                      label="Store Handle (Your Custom Link)"
                      data-testid="onboarding-shop-slug"
                      placeholder="studio-craft"
                      value={handle.slug}
                      onChange={onSlug}
                    />

                    {/* Live link preview and availability status */}
                    <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
                      <p
                        className="text-xs font-medium text-[#525252]"
                        data-testid="onboarding-slug-preview"
                      >
                        Your link:{" "}
                        <span className="font-mono font-bold text-[#0A0A0A]">
                          marketo.com/{handle.slug || "your-store"}
                        </span>
                      </p>

                      {handle.slug && (
                        <div className="flex items-center gap-1.5 text-xs font-bold">
                          {checkingSlug ? (
                            <span className="flex items-center gap-1 text-neutral-500">
                              <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#FF4F00]" /> Checking availability...
                            </span>
                          ) : slugStatus === "available" ? (
                            <motion.span
                              initial={{ opacity: 0, scale: 0.8 }}
                              animate={{ opacity: 1, scale: 1 }}
                              className="flex items-center gap-1 border border-[#0B5227] bg-[#E6F6EC] px-2 py-0.5 text-[#0B5227]"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" /> Handle is available!
                            </motion.span>
                          ) : slugStatus === "taken" ? (
                            <motion.span
                              initial={{ opacity: 0, scale: 0.8 }}
                              animate={{ opacity: 1, scale: 1 }}
                              className="flex items-center gap-1 border border-[#8A2200] bg-[#FFEAE5] px-2 py-0.5 text-[#8A2200]"
                            >
                              <AlertCircle className="h-3.5 w-3.5" /> Handle is already taken
                            </motion.span>
                          ) : null}
                        </div>
                      )}
                    </div>
                  </div>

                  <label className="block">
                    <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">
                      Store Bio (optional)
                    </span>
                    <textarea
                      data-testid="onboarding-shop-bio"
                      rows={2}
                      placeholder="Tell buyers what you make and sell."
                      value={handle.bio || ""}
                      onChange={(e) => setHandle((h) => ({ ...h, bio: e.target.value }))}
                      className="mt-1.5 w-full resize-none border-2 border-[#0A0A0A] bg-white px-3 py-2.5 text-sm outline-none transition-colors placeholder:text-neutral-400 focus:border-[#FF4F00]"
                    />
                  </label>
                </div>

                {handleErr && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-5"
                  >
                    <Note tone="error" data-testid="onboarding-handle-error">
                      {handleErr}
                    </Note>
                  </motion.div>
                )}

                <div className="mt-8 flex items-center justify-between border-t-2 border-neutral-100 pt-6">
                  <button
                    type="button"
                    onClick={() => setStep(0)}
                    className="text-xs font-bold uppercase tracking-wider text-neutral-500 transition-colors hover:text-[#0A0A0A]"
                  >
                    ← Back
                  </button>

                  <Btn
                    variant="primary"
                    data-testid="onboarding-handle-next"
                    onClick={createShop}
                    disabled={busy || slugStatus === "taken" || !handle.name.trim()}
                  >
                    {busy ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" /> Setting up...
                      </>
                    ) : (
                      <>
                        Continue to Profile Photo <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </Btn>
                </div>
              </div>
            </motion.div>
          )}

          {/* SCREEN 3: Store Profile Picture (PFP) */}
          {step === 2 && (
            <motion.div
              key="photo-screen"
              variants={screenVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              data-testid="onboarding-photo"
            >
              <div className="border-2 border-[#0A0A0A] bg-white p-6 shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] sm:p-8">
                <div className="mb-2 inline-flex items-center gap-2 border border-[#0A0A0A] bg-[#FFF4E0] px-2.5 py-1 text-xs font-black uppercase tracking-wider text-[#FF4F00]">
                  Step 2 of 2
                </div>
                <h1 className="mk-head text-3xl font-black tracking-tighter sm:text-4xl">
                  Add your store profile photo
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-[#525252]">
                  Add a face, brand icon, or logo to your profile. You can always change this later.
                </p>

                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.1, duration: 0.4 }}
                  className="my-8 flex flex-col items-center justify-center rounded-sm border-2 border-dashed border-neutral-300 bg-[#FAFAFA] p-8 text-center"
                >
                  <div className="relative mb-4">
                    <div className="rounded-full ring-4 ring-[#FF4F00]/20 p-1 shadow-md">
                      <ImageUpload
                        value={avatar}
                        onChange={setAvatar}
                        kind="avatar"
                        shape="round"
                        label="Upload Photo"
                        testId="onboarding-avatar"
                      />
                    </div>
                  </div>
                  <p className="text-xs font-medium text-neutral-500">
                    Square PNG or JPG recommended (at least 300×300px)
                  </p>
                </motion.div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t-2 border-neutral-100 pt-6">
                  <button
                    type="button"
                    onClick={finish}
                    data-testid="onboarding-photo-skip"
                    className="order-2 text-center text-xs font-bold uppercase tracking-wider text-neutral-600 underline transition-colors hover:text-[#FF4F00] sm:order-1"
                  >
                    Add later / Skip for now
                  </button>

                  <Btn
                    variant="primary"
                    data-testid="onboarding-photo-next"
                    onClick={finish}
                    disabled={busy}
                    className="order-1 sm:order-2"
                  >
                    {busy ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" /> Entering profile...
                      </>
                    ) : (
                      <>
                        Go to My Store Profile <Sparkles className="h-4 w-4" />
                      </>
                    )}
                  </Btn>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

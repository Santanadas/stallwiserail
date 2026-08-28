import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { 
  auth, 
  googleProvider, 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
  sendEmailVerification,
  onAuthStateChanged
} from "@/lib/firebase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      if (fbUser) {
        setUser({
          user_id: fbUser.uid,
          email: fbUser.email,
          name: fbUser.displayName || fbUser.email?.split("@")[0] || "Seller",
          picture: fbUser.photoURL || "",
          subscriptionStatus: "Community",
          emailVerified: fbUser.emailVerified,
          authProvider: fbUser.providerData?.[0]?.providerId || "firebase"
        });
        setLoading(false);
      } else {
        checkAuth();
      }
    });

    return () => unsubscribe();
  }, [checkAuth]);

  const loginWithGoogle = async () => {
    const res = await signInWithPopup(auth, googleProvider);
    const fbUser = res.user;
    const userData = {
      user_id: fbUser.uid,
      email: fbUser.email,
      name: fbUser.displayName || fbUser.email?.split("@")[0] || "Seller",
      picture: fbUser.photoURL || "",
      subscriptionStatus: "Community",
      emailVerified: true,
      authProvider: "google"
    };
    setUser(userData);
    return userData;
  };

  const loginWithEmail = async (email, password) => {
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setUser(data);
      return data;
    } catch (apiErr) {
      try {
        const res = await signInWithEmailAndPassword(auth, email, password);
        const fbUser = res.user;
        const userData = {
          user_id: fbUser.uid,
          email: fbUser.email,
          name: fbUser.displayName || fbUser.email?.split("@")[0] || "Seller",
          picture: fbUser.photoURL || "",
          subscriptionStatus: "Community",
          emailVerified: fbUser.emailVerified,
          authProvider: "password"
        };
        setUser(userData);
        return userData;
      } catch {
        throw apiErr;
      }
    }
  };

  const registerWithEmail = async ({ name, email, password }) => {
    try {
      const { data } = await api.post("/auth/register", { name, email, password });
      setUser(data);
      return data;
    } catch (apiErr) {
      try {
        const res = await createUserWithEmailAndPassword(auth, email, password);
        const fbUser = res.user;
        try {
          await sendEmailVerification(fbUser);
        } catch (e) {
          console.warn("Failed to send email verification:", e);
        }
        const userData = {
          user_id: fbUser.uid,
          email: fbUser.email,
          name: name || fbUser.email?.split("@")[0] || "Seller",
          picture: "",
          subscriptionStatus: "Community",
          emailVerified: false,
          authProvider: "password"
        };
        setUser(userData);
        return userData;
      } catch {
        throw apiErr;
      }
    }
  };

  const sendVerificationEmail = async () => {
    if (auth.currentUser) {
      await sendEmailVerification(auth.currentUser);
      return { message: "Verification email sent. Please check your inbox and spam folder." };
    }
    throw new Error("No active session found. Please log in first.");
  };

  const checkEmailVerified = async () => {
    if (auth.currentUser) {
      await auth.currentUser.reload();
      const updated = auth.currentUser;
      const isVerified = updated.emailVerified;
      if (isVerified) {
        setUser((prev) => (prev ? { ...prev, emailVerified: true } : prev));
      }
      return isVerified;
    }
    return false;
  };

  const resetPassword = async (email) => {
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      return data;
    } catch {
      await sendPasswordResetEmail(auth, email);
      return { message: "Password reset link sent to your email." };
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {}
    try {
      await firebaseSignOut(auth);
    } catch {}
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      setUser, 
      loading, 
      checkAuth, 
      logout,
      loginWithGoogle,
      loginWithEmail,
      registerWithEmail,
      sendVerificationEmail,
      checkEmailVerified,
      resetPassword
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      // If access token expired, try silent refresh with the 90-day refresh token
      try {
        const { data: refreshed } = await api.post("/auth/refresh");
        setUser(refreshed);
      } catch {
        setUser(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  /**
   * Submit login credentials. Returns { pendingOtp, email, otpId }
   * instead of the user — caller must complete OTP verification.
   */
  const loginWithEmail = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    return data; // { pendingOtp: true, email, otpId }
  };

  /**
   * Submit registration. Returns { pendingOtp, email, otpId }
   * instead of the user — caller must complete OTP verification.
   */
  const registerWithEmail = async ({ name, email, password }) => {
    const { data } = await api.post("/auth/register", { name, email, password });
    return data; // { pendingOtp: true, email, otpId }
  };

  /**
   * Called after successful OTP verification — sets the authenticated user.
   */
  const setVerifiedUser = (userData) => {
    setUser(userData);
  };

  const resetPassword = async (email) => {
    const { data } = await api.post("/auth/forgot-password", { email });
    return data;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
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
      loginWithEmail,
      registerWithEmail,
      setVerifiedUser,
      resetPassword
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

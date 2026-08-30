import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const cached = localStorage.getItem("stallwise_user");
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(!user);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      try {
        localStorage.setItem("stallwise_user", JSON.stringify(data));
      } catch {}
    } catch {
      // If access token expired, try silent refresh with the 1-year refresh token
      try {
        const { data: refreshed } = await api.post("/auth/refresh");
        setUser(refreshed);
        try {
          localStorage.setItem("stallwise_user", JSON.stringify(refreshed));
        } catch {}
      } catch {
        setUser(false);
        try {
          localStorage.removeItem("stallwise_user");
          localStorage.removeItem("stallwise_token");
        } catch {}
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
    try {
      localStorage.setItem("stallwise_user", JSON.stringify(userData));
      if (userData?.token) {
        localStorage.setItem("stallwise_token", userData.token);
      }
    } catch {}
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
    try {
      localStorage.removeItem("stallwise_user");
      localStorage.removeItem("stallwise_token");
    } catch {}
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

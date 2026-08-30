import axios from "axios";

const backendUrl =
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_BACKEND_URL) ||
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_BACKEND_URL) ||
  "";

export const API = `${backendUrl}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request Interceptor: Attach persistent token from localStorage
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem("stallwise_token") || sessionStorage.getItem("stallwise_token");
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {}
  return config;
});

// Response Interceptor: Automatically refresh expired access tokens using the 90-day refresh token
api.interceptors.response.use(
  (response) => {
    // Auto-persist returned token in localStorage or sessionStorage
    if (response?.data?.token) {
      try {
        const storage = localStorage.getItem("stallwise_user") ? localStorage : sessionStorage;
        storage.setItem("stallwise_token", response.data.token);
      } catch {}
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Do not attempt refresh on auth endpoints (login, register, verify-otp, refresh itself)
    const isAuthEndpoint =
      originalRequest?.url?.includes("/auth/login") ||
      originalRequest?.url?.includes("/auth/register") ||
      originalRequest?.url?.includes("/auth/verify-otp") ||
      originalRequest?.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => api(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data: refData } = await api.post("/auth/refresh");
        if (refData?.token) {
          try {
            const storage = localStorage.getItem("stallwise_user") ? localStorage : sessionStorage;
            storage.setItem("stallwise_token", refData.token);
          } catch {}
        }
        processQueue(null);
        return api(originalRequest);
      } catch (refreshErr) {
        try {
          localStorage.removeItem("stallwise_token");
          sessionStorage.removeItem("stallwise_token");
        } catch {}
        processQueue(refreshErr, null);
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default api;

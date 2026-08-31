import "@/App.css";
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth, hasStoredSession } from "@/context/AuthContext";

/**
 * Every route is code-split. Before this the whole app — dashboard, product
 * editor, framer-motion, all of it — shipped in one ~614 kB chunk that a buyer
 * landing on a shop page had to download before anything rendered. Now each
 * route pulls only its own chunk.
 */
const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));
const ForgotPassword = lazy(() => import("@/pages/ForgotPassword"));
const ResetPassword = lazy(() => import("@/pages/ResetPassword"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Onboarding = lazy(() => import("@/pages/Onboarding"));
const OrderDetail = lazy(() => import("@/pages/OrderDetail"));
const Shop = lazy(() => import("@/pages/Shop"));
const ProductPage = lazy(() => import("@/pages/ProductPage"));
const Shops = lazy(() => import("@/pages/Shops"));
const BuyerOrder = lazy(() => import("@/pages/BuyerOrder"));
const About = lazy(() => import("@/pages/About"));
const SellOnline = lazy(() => import("@/pages/SellOnline"));
const Terms = lazy(() => import("@/pages/Terms"));
const Privacy = lazy(() => import("@/pages/Privacy"));
const Contact = lazy(() => import("@/pages/Contact"));

function RouteFallback() {
  return (
    <div className="mk flex min-h-screen items-center justify-center bg-[#FAFAFA]">
      <div className="h-7 w-7 animate-spin rounded-full border-2 border-neutral-300 border-t-[#FF4F00]" />
    </div>
  );
}

/**
 * The landing page is for signed-out visitors. Anyone already signed in goes
 * straight to their dashboard without the landing page rendering first.
 *
 * We only block on `loading` when the browser actually shows signs of a
 * session. Otherwise an anonymous visitor — and Googlebot — would sit behind a
 * spinner waiting for /auth/me to 401 before the homepage painted, which would
 * cost us LCP on the one page we most want ranking.
 */
function RootRoute() {
  const { user, loading } = useAuth();
  if (loading && hasStoredSession()) return <RouteFallback />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Landing />;
}

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <RouteFallback />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<RootRoute />} />
        <Route path="/shops" element={<Shops />} />
        <Route path="/sell-online" element={<SellOnline />} />
        <Route path="/about" element={<About />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
        <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
        <Route path="/orders/:orderId" element={<Protected><OrderDetail /></Protected>} />
        <Route path="/order/:orderId" element={<BuyerOrder />} />
        {/* Storefront routes last — these are the catch-alls. */}
        <Route path="/:storeSlug" element={<Shop />} />
        <Route path="/:storeSlug/:productSlug" element={<ProductPage />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

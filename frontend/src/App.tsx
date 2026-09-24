import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import MobileNav from "./components/MobileNav";
import { useAuth } from "./hooks/useAuth";
import Home from "./pages/Home";
import Overview from "./pages/Overview";
import Transactions from "./pages/Transactions";
import Categories from "./pages/Categories";
import Subscriptions from "./pages/Subscriptions";
import Anomalies from "./pages/Anomalies";
import AskAI from "./pages/AskAI";
import UploadPage from "./pages/Upload";
import HowItWorks from "./pages/HowItWorks";
import Login from "./pages/Login";
import Register from "./pages/Register";

/** Signed-in chrome: sidebar on desktop, bottom tab bar on phones. */
function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-bg">
      <Sidebar />
      <main id="main" className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 pb-[calc(4.5rem+env(safe-area-inset-bottom))] pt-5 md:px-8 md:py-8">
          {children}
        </div>
      </main>
      <MobileNav />
    </div>
  );
}

function AppRoutes() {
  return (
    <AppShell>
      <Routes>
        <Route path="/ask" element={<AskAI />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/anomalies" element={<Anomalies />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="*" element={<Navigate to="/ask" replace />} />
      </Routes>
    </AppShell>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Home />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Register />} />
      {/* Public too: the landing links here, and recruiters shouldn't need an account to read it. */}
      {!isAuthenticated && <Route path="/how-it-works" element={<HowItWorks />} />}
      <Route path="/*" element={isAuthenticated ? <AppRoutes /> : <Navigate to="/login" replace />} />
    </Routes>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import { useAuth } from "./hooks/useAuth";
import Home from "./pages/Home";
import Overview from "./pages/Overview";
import Transactions from "./pages/Transactions";
import Categories from "./pages/Categories";
import Subscriptions from "./pages/Subscriptions";
import Anomalies from "./pages/Anomalies";
import AskAI from "./pages/AskAI";
import UploadPage from "./pages/Upload";
import Login from "./pages/Login";
import Register from "./pages/Register";

function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-8">
          <Routes>
            <Route path="/ask" element={<AskAI />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/anomalies" element={<Anomalies />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="*" element={<Navigate to="/ask" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Home />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Login />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/ask" replace /> : <Register />} />
      <Route path="/*" element={isAuthenticated ? <AppLayout /> : <Navigate to="/login" replace />} />
    </Routes>
  );
}

import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Overview from "./pages/Overview";
import Transactions from "./pages/Transactions";
import Categories from "./pages/Categories";
import Subscriptions from "./pages/Subscriptions";
import Anomalies from "./pages/Anomalies";
import AskAI from "./pages/AskAI";
import UploadPage from "./pages/Upload";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/anomalies" element={<Anomalies />} />
            <Route path="/ask" element={<AskAI />} />
            <Route path="/upload" element={<UploadPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

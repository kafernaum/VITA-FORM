import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "sonner";
import Navbar from "@/components/Navbar";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Theorie from "@/pages/Theorie";
import Generator from "@/pages/Generator";
import Preview from "@/pages/Preview";
import Library from "@/pages/Library";
import Analyse from "@/pages/Analyse";
import Auteur from "@/pages/Auteur";
import Admin from "@/pages/Admin";
import PaymentSuccess from "@/pages/PaymentSuccess";
import "@/App.css";

function ProtectedRoute({ children, adminOnly = false }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (!user) return <Navigate to={`/auth?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

function Shell({ children }) {
  return (
    <div className="vf-page vf-grain relative">
      <Navbar />
      <main className="pt-20 relative z-10">{children}</main>
      <footer className="border-t border-white/5 mt-24 py-10 text-center text-xs text-slate-500">
        <div className="vf-mono tracking-[0.3em]">VITA-FORM · DOCTRINA VITALIS</div>
        <div className="mt-2">© {new Date().getFullYear()} — Théorie Vitaliste des Finances Publiques · Pr. Ahmed ELY Mustapha</div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" theme="dark" richColors />
        <Routes>
          <Route path="/" element={<Shell><Landing /></Shell>} />
          <Route path="/auth" element={<Shell><Auth /></Shell>} />
          <Route path="/theorie" element={<Shell><Theorie /></Shell>} />
          <Route path="/auteur" element={<Shell><Auteur /></Shell>} />
          <Route path="/generator" element={<Shell><ProtectedRoute><Generator /></ProtectedRoute></Shell>} />
          <Route path="/analyse" element={<Shell><ProtectedRoute><Analyse /></ProtectedRoute></Shell>} />
          <Route path="/library" element={<Shell><ProtectedRoute><Library /></ProtectedRoute></Shell>} />
          <Route path="/preview/:id" element={<Shell><ProtectedRoute><Preview /></ProtectedRoute></Shell>} />
          <Route path="/payment/success" element={<Shell><ProtectedRoute><PaymentSuccess /></ProtectedRoute></Shell>} />
          <Route path="/admin" element={<Shell><ProtectedRoute adminOnly><Admin /></ProtectedRoute></Shell>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

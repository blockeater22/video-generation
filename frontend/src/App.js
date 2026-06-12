import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import DashboardLayout from "@/components/layout/DashboardLayout";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ForgotPassword from "@/pages/ForgotPassword";
import Dashboard from "@/pages/Dashboard";
import Videos from "@/pages/Videos";
import Avatars from "@/pages/Avatars";
import Voices from "@/pages/Voices";
import Editor from "@/pages/Editor";
import Projects from "@/pages/Projects";
import Settings from "@/pages/Settings";
import ApiKeys from "@/pages/ApiKeys";
import Webhooks from "@/pages/Webhooks";
import Team from "@/pages/Team";
import Billing from "@/pages/Billing";
import Developer from "@/pages/Developer";

const Splash = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <Loader2 className="animate-spin text-accent" size={28} />
  </div>
);

const Protected = ({ children }) => {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <Splash />;
  if (status === "guest") return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
};

const GuestOnly = ({ children }) => {
  const { status } = useAuth();
  if (status === "loading") return <Splash />;
  if (status === "authed") return <Navigate to="/" replace />;
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route path="/forgot-password" element={<GuestOnly><ForgotPassword /></GuestOnly>} />

      <Route element={<Protected><DashboardLayout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/videos" element={<Videos />} />
        <Route path="/avatars" element={<Avatars />} />
        <Route path="/voices" element={<Voices />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/api-keys" element={<ApiKeys />} />
        <Route path="/webhooks" element={<Webhooks />} />
        <Route path="/developer" element={<Developer />} />
        <Route path="/team" element={<Team />} />
        <Route path="/billing" element={<Billing />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="/editor" element={<Protected><Editor /></Protected>} />
      <Route path="/editor/:id" element={<Protected><Editor /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
      <Toaster position="top-right" theme="dark" richColors />
    </div>
  );
}

export default App;

import { Outlet, useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/context/AuthContext";

export const DashboardLayout = () => {
  const navigate = useNavigate();
  const { org } = useAuth();

  return (
    <div className="min-h-screen bg-background grid-bg">
      <Sidebar />
      <div className="lg:pl-64 flex flex-col min-h-screen">
        <header className="h-16 border-b border-border bg-background/80 backdrop-blur-xl sticky top-0 z-30 flex items-center justify-between px-6">
          <div className="lg:hidden font-display font-extrabold tracking-tight text-lg">AvatarPlatform</div>
          <div className="flex-1" />
          <div className="flex items-center gap-3">
            {org && (
              <Badge data-testid="topbar-plan-badge" variant="outline"
                className="uppercase tracking-wider text-xs font-semibold border-border bg-secondary">
                {org.plan} plan
              </Badge>
            )}
            <Button data-testid="topbar-create-video-btn" onClick={() => navigate("/editor")} size="sm"
              className="bg-accent text-white hover:bg-accent/90 gap-1.5">
              <Plus size={15} /> New
            </Button>
          </div>
        </header>
        <main className="flex-1 w-full max-w-screen-2xl mx-auto px-4 md:px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;

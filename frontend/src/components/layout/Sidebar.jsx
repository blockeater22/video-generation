import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Clapperboard, Users, AudioLines, FolderKanban, Settings,
  Clapperboard as Logo, Plus, KeyRound, Webhook, UsersRound, CreditCard, Code2, LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

const groups = [
  {
    label: "Studio",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/videos", label: "Videos", icon: Clapperboard },
      { to: "/avatars", label: "Avatars", icon: Users },
      { to: "/voices", label: "Voices", icon: AudioLines },
      { to: "/projects", label: "Projects", icon: FolderKanban },
    ],
  },
  {
    label: "Developer",
    items: [
      { to: "/api-keys", label: "API Keys", icon: KeyRound },
      { to: "/webhooks", label: "Webhooks", icon: Webhook },
      { to: "/developer", label: "API Docs", icon: Code2 },
    ],
  },
  {
    label: "Organization",
    items: [
      { to: "/team", label: "Team", icon: UsersRound },
      { to: "/billing", label: "Billing", icon: CreditCard },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export const Sidebar = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <aside data-testid="sidebar" className="w-64 fixed inset-y-0 left-0 border-r border-border bg-background z-40 hidden lg:flex lg:flex-col">
      <div className="h-16 flex items-center gap-2.5 px-6 border-b border-border">
        <div className="h-8 w-8 rounded-md bg-accent flex items-center justify-center">
          <Logo className="text-white" size={18} />
        </div>
        <span className="font-display font-extrabold tracking-tight text-lg">AvatarPlatform</span>
      </div>

      <div className="p-4">
        <Button data-testid="sidebar-create-video-btn" onClick={() => navigate("/editor")}
          className="w-full bg-accent text-white hover:bg-accent/90 font-semibold gap-2 shadow-[0_0_18px_rgba(239,68,68,0.25)]">
          <Plus size={16} /> Create Video
        </Button>
      </div>

      <nav className="flex-1 px-3 space-y-5 overflow-y-auto pb-4">
        {groups.map((g) => (
          <div key={g.label}>
            <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">{g.label}</div>
            <div className="space-y-0.5">
              {g.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                      isActive ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`
                  }>
                  <Icon size={17} /> {label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold flex-shrink-0">
            {(user?.full_name || user?.email || "?").charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate">{user?.full_name || "User"}</div>
            <div className="text-xs text-muted-foreground truncate">{user?.email}</div>
          </div>
          <button onClick={logout} data-testid="logout-btn" className="text-muted-foreground hover:text-red-400 transition-colors">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

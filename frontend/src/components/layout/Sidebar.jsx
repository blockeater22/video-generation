import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Clapperboard, Users, AudioLines, FolderKanban, Settings, Clapperboard as Logo, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/videos", label: "Videos", icon: Clapperboard },
  { to: "/avatars", label: "Avatars", icon: Users },
  { to: "/voices", label: "Voices", icon: AudioLines },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar = () => {
  const navigate = useNavigate();
  return (
    <aside
      data-testid="sidebar"
      className="w-64 fixed inset-y-0 left-0 border-r border-border bg-background z-40 hidden lg:flex lg:flex-col"
    >
      <div className="h-16 flex items-center gap-2.5 px-6 border-b border-border">
        <div className="h-8 w-8 rounded-md bg-accent flex items-center justify-center">
          <Logo className="h-4.5 w-4.5 text-white" size={18} />
        </div>
        <span className="font-display font-extrabold tracking-tight text-lg">AvatarPlatform</span>
      </div>

      <div className="p-4">
        <Button
          data-testid="sidebar-create-video-btn"
          onClick={() => navigate("/editor")}
          className="w-full bg-accent text-white hover:bg-accent/90 font-semibold gap-2 shadow-[0_0_18px_rgba(239,68,68,0.25)]"
        >
          <Plus size={16} /> Create Video
        </Button>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            data-testid={`nav-${label.toLowerCase()}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="text-xs text-muted-foreground font-mono">v0.1.0 · Phase 1</div>
      </div>
    </aside>
  );
};

export default Sidebar;

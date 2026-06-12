import { Clapperboard } from "lucide-react";

export const AuthShell = ({ title, subtitle, children, footer }) => (
  <div className="min-h-screen flex grid-bg" data-testid="auth-shell">
    {/* Left brand panel */}
    <div className="hidden lg:flex w-1/2 flex-col justify-between p-12 border-r border-border relative overflow-hidden">
      <div className="flex items-center gap-2.5">
        <div className="h-9 w-9 rounded-md bg-accent flex items-center justify-center">
          <Clapperboard size={20} className="text-white" />
        </div>
        <span className="font-display font-extrabold tracking-tight text-xl">AvatarPlatform</span>
      </div>
      <div>
        <h2 className="font-display text-4xl font-bold tracking-tight leading-tight">
          Lifelike AI avatars.<br /><span className="text-accent">Studio-grade</span> video.
        </h2>
        <p className="text-muted-foreground mt-4 max-w-md leading-relaxed">
          Generate photorealistic talking-head videos from text. A developer-first platform with a polished editor and a first-class API.
        </p>
      </div>
      <div className="flex gap-8 text-sm font-mono text-muted-foreground">
        <div><span className="text-foreground font-semibold">&lt;500ms</span> · real-time</div>
        <div><span className="text-foreground font-semibold">100+</span> avatars</div>
        <div><span className="text-foreground font-semibold">20+</span> languages</div>
      </div>
    </div>

    {/* Right form */}
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="lg:hidden flex items-center gap-2.5 mb-8 justify-center">
          <div className="h-8 w-8 rounded-md bg-accent flex items-center justify-center">
            <Clapperboard size={18} className="text-white" />
          </div>
          <span className="font-display font-extrabold tracking-tight text-lg">AvatarPlatform</span>
        </div>
        <h1 className="font-display text-3xl font-bold tracking-tight">{title}</h1>
        {subtitle && <p className="text-muted-foreground mt-1.5 text-sm">{subtitle}</p>}
        <div className="mt-8">{children}</div>
        {footer && <div className="mt-6 text-sm text-muted-foreground text-center">{footer}</div>}
      </div>
    </div>
  </div>
);

export default AuthShell;

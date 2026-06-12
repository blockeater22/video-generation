import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Zap, ShieldCheck, LogOut } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Settings() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user, org, logout, refreshOrg } = useAuth();
  const [name, setName] = useState(org?.name || "");

  const save = useMutation({
    mutationFn: () => api.updateOrg({ name }),
    onSuccess: async () => { await refreshOrg(); qc.invalidateQueries({ queryKey: ["org"] }); toast.success("Saved"); },
  });

  if (!org) return null;

  return (
    <div className="space-y-8 max-w-3xl" data-testid="settings-page">
      <div>
        <h1 className="font-display text-4xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Organization and account configuration.</p>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center gap-2 mb-5"><Building2 size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Organization</h3></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div><Label className="mb-1.5 block">Name</Label><Input data-testid="settings-org-name" value={name} onChange={(e) => setName(e.target.value)} /></div>
          <div><Label className="mb-1.5 block">Slug</Label><Input value={org.slug} className="font-mono" disabled /></div>
        </div>
        <Button data-testid="settings-save-btn" onClick={() => save.mutate()} disabled={save.isPending || name === org.name}
          className="mt-4 bg-accent text-white hover:bg-accent/90">Save changes</Button>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2"><Zap size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Plan</h3></div>
          <Badge variant="outline" className="uppercase tracking-wider text-xs font-semibold bg-secondary">{org.plan}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">{org.credits_used} / {org.credits_limit} video credits used this period.</p>
        <Button data-testid="settings-billing-btn" variant="secondary" className="mt-4" onClick={() => navigate("/billing")}>Manage billing</Button>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center gap-2 mb-4"><ShieldCheck size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Account</h3></div>
        <p className="text-sm text-muted-foreground">Signed in as <span className="text-foreground font-medium">{user?.email}</span></p>
        <Button data-testid="settings-logout-btn" variant="ghost" className="mt-4 text-red-400 hover:text-red-300 gap-2 px-0" onClick={logout}>
          <LogOut size={15} /> Sign out
        </Button>
      </div>
    </div>
  );
}

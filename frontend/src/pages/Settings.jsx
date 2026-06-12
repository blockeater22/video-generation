import { useQuery } from "@tanstack/react-query";
import { Building2, Zap, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";

const PLANS = [
  { name: "Free", price: "$0", videos: "3 / mo", res: "720p", api: "No" },
  { name: "Starter", price: "$29", videos: "50 / mo", res: "1080p", api: "Yes" },
  { name: "Pro", price: "$99", videos: "300 / mo", res: "1080p + 4K", api: "Yes" },
  { name: "Enterprise", price: "Custom", videos: "Unlimited", res: "4K", api: "Yes" },
];

export default function Settings() {
  const { data: org, isLoading } = useQuery({ queryKey: ["org"], queryFn: api.org });

  if (isLoading) return <Skeleton className="h-96" />;

  return (
    <div className="space-y-8 max-w-4xl" data-testid="settings-page">
      <div>
        <h1 className="font-display text-4xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Organization and plan configuration.</p>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center gap-2 mb-5"><Building2 size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Organization</h3></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div><Label className="mb-1.5 block">Name</Label><Input defaultValue={org.name} data-testid="settings-org-name" /></div>
          <div><Label className="mb-1.5 block">Slug</Label><Input defaultValue={org.slug} className="font-mono" disabled /></div>
        </div>
        <p className="text-xs text-muted-foreground mt-3">Auth & multi-user management arrive in a later phase.</p>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2"><Zap size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Plan & Billing</h3></div>
          <Badge variant="outline" className="uppercase tracking-wider text-xs font-semibold bg-secondary">{org.plan}</Badge>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {PLANS.map((p) => {
            const active = p.name.toLowerCase() === org.plan;
            return (
              <div key={p.name} className={`rounded-md border p-4 ${active ? "border-accent bg-accent/5" : "border-border"}`} data-testid={`plan-${p.name.toLowerCase()}`}>
                <div className="font-display font-semibold">{p.name}</div>
                <div className="font-mono text-2xl font-bold mt-1">{p.price}</div>
                <div className="text-xs text-muted-foreground mt-3 space-y-1">
                  <div>{p.videos}</div><div>{p.res}</div><div>API: {p.api}</div>
                </div>
                {active && <Badge className="mt-3 bg-accent text-white border-0 text-[10px]">CURRENT</Badge>}
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground mt-4 flex items-center gap-1.5"><ShieldCheck size={13} /> Stripe billing integration is planned for a later phase.</p>
      </div>
    </div>
  );
}

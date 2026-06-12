import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Billing() {
  const { org, refreshOrg } = useAuth();
  const [params, setParams] = useSearchParams();
  const [polling, setPolling] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["plans"], queryFn: api.billingPlans });

  const checkout = useMutation({
    mutationFn: (plan) => api.billingCheckout({ plan, origin_url: window.location.origin }),
    onSuccess: (d) => { window.location.href = d.url; },
    onError: () => toast.error("Could not start checkout"),
  });

  // Poll payment status when returning from Stripe
  useEffect(() => {
    const sid = params.get("session_id");
    if (!sid) return;
    setPolling(true);
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const s = await api.billingStatus(sid);
        if (s.payment_status === "paid") {
          toast.success("Plan upgraded!");
          await refreshOrg();
          setPolling(false);
          setParams({});
          return;
        }
        if (s.status === "expired" || attempts >= 6) {
          setPolling(false);
          setParams({});
          return;
        }
      } catch { /* keep trying */ }
      setTimeout(poll, 2000);
    };
    poll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8 max-w-5xl" data-testid="billing-page">
      <div>
        <h1 className="font-display text-4xl font-bold tracking-tight">Billing & Plans</h1>
        <p className="text-muted-foreground mt-1">Upgrade to unlock more videos and higher resolution.</p>
      </div>

      {polling && (
        <div className="bg-card border border-border rounded-md p-4 flex items-center gap-3" data-testid="billing-polling">
          <Loader2 className="animate-spin text-accent" size={18} /> Confirming your payment…
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-80" />)}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="billing-plans">
          {data.plans.map((p) => {
            const active = org?.plan === p.id;
            const upgradeable = p.id === "starter" || p.id === "pro";
            return (
              <div key={p.id} className={`rounded-md border p-6 flex flex-col ${active ? "border-accent bg-accent/5" : "border-border bg-card"}`} data-testid={`plan-card-${p.id}`}>
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-xl font-bold">{p.name}</h3>
                  {active && <Badge className="bg-accent text-white border-0 text-[10px]">CURRENT</Badge>}
                </div>
                <div className="mt-3 font-mono">
                  {p.price === null ? <span className="text-2xl font-bold">Custom</span> : <><span className="text-3xl font-bold">${p.price}</span><span className="text-muted-foreground text-sm">/mo</span></>}
                </div>
                <ul className="mt-5 space-y-2 text-sm text-muted-foreground flex-1">
                  <li className="flex items-center gap-2"><Check size={14} className="text-accent" /> {p.credits} videos/mo</li>
                  <li className="flex items-center gap-2"><Check size={14} className="text-accent" /> {p.resolution}</li>
                  <li className="flex items-center gap-2"><Check size={14} className="text-accent" /> {p.api ? "API access" : "No API"}</li>
                  <li className="flex items-center gap-2"><Check size={14} className="text-accent" /> {p.members} members</li>
                </ul>
                <div className="mt-6">
                  {active ? (
                    <Button disabled variant="secondary" className="w-full">Current plan</Button>
                  ) : p.id === "enterprise" ? (
                    <Button variant="secondary" className="w-full" onClick={() => toast.info("Contact sales@avatarplatform.io")}>Contact Sales</Button>
                  ) : p.id === "free" ? (
                    <Button disabled variant="ghost" className="w-full text-muted-foreground">Free tier</Button>
                  ) : (
                    <Button
                      data-testid={`upgrade-${p.id}`}
                      disabled={checkout.isPending}
                      onClick={() => checkout.mutate(p.id)}
                      className="w-full bg-accent text-white hover:bg-accent/90 gap-2"
                    >
                      {checkout.isPending ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />} Upgrade
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <p className="text-xs text-muted-foreground font-mono">Payments processed securely via Stripe (test mode).</p>
    </div>
  );
}

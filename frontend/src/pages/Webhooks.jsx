import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Webhook, Send, ChevronDown } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

const EVENTS = ["video.completed", "video.failed"];

function Deliveries({ webhookId }) {
  const { data } = useQuery({ queryKey: ["deliveries", webhookId], queryFn: () => api.webhookDeliveries(webhookId) });
  if (!data?.length) return <p className="text-xs text-muted-foreground p-3">No deliveries yet.</p>;
  return (
    <div className="divide-y divide-border">
      {data.map((d) => (
        <div key={d.id} className="flex items-center justify-between p-3 text-xs">
          <span className="font-mono">{d.event_type}</span>
          <span className={`font-mono ${d.success ? "text-emerald-400" : "text-red-400"}`}>{d.response_status || "ERR"}</span>
        </div>
      ))}
    </div>
  );
}

export default function Webhooks() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [expanded, setExpanded] = useState(null);

  const { data, isLoading } = useQuery({ queryKey: ["webhooks"], queryFn: api.listWebhooks });
  const create = useMutation({
    mutationFn: api.createWebhook,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["webhooks"] }); toast.success("Webhook added"); setOpen(false); setUrl(""); },
  });
  const del = useMutation({
    mutationFn: api.deleteWebhook,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["webhooks"] }); toast.success("Webhook deleted"); },
  });
  const test = useMutation({
    mutationFn: api.testWebhook,
    onSuccess: () => { toast.success("Test event dispatched"); qc.invalidateQueries({ queryKey: ["deliveries"] }); },
  });

  return (
    <div className="space-y-6" data-testid="webhooks-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Webhooks</h1>
          <p className="text-muted-foreground mt-1">Get notified when videos complete or fail.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="webhook-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> Add Endpoint</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><Webhook size={18} className="text-accent" /> Add Webhook</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div><Label className="mb-1.5 block">Endpoint URL</Label><Input data-testid="webhook-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yourapp.com/webhooks" /></div>
              <div className="flex gap-2">{EVENTS.map((e) => <Badge key={e} variant="outline" className="font-mono text-xs">{e}</Badge>)}</div>
            </div>
            <DialogFooter>
              <Button data-testid="webhook-submit" disabled={!url || create.isPending} onClick={() => create.mutate({ url, events: EVENTS })} className="bg-accent text-white hover:bg-accent/90">Add Endpoint</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : data.length === 0 ? (
        <div className="border border-dashed border-border rounded-md py-16 text-center">
          <Webhook className="mx-auto text-muted-foreground mb-3" size={28} />
          <p className="text-muted-foreground">No webhooks configured.</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="webhooks-list">
          {data.map((w) => (
            <div key={w.id} className="bg-card border border-border rounded-md overflow-hidden">
              <div className="flex items-center gap-4 p-4">
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-sm truncate">{w.url}</div>
                  <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
                    {w.events.map((e) => <span key={e} className="font-mono">{e}</span>)}
                    {w.failure_count > 0 && <StatusBadge status="failed" />}
                  </div>
                </div>
                <Button size="sm" variant="secondary" className="gap-1.5" onClick={() => test.mutate(w.id)} data-testid={`webhook-test-${w.id}`}><Send size={13} /> Test</Button>
                <Button size="sm" variant="ghost" onClick={() => setExpanded(expanded === w.id ? null : w.id)} data-testid={`webhook-expand-${w.id}`}><ChevronDown size={15} className={expanded === w.id ? "rotate-180 transition-transform" : "transition-transform"} /></Button>
                <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400" onClick={() => del.mutate(w.id)} data-testid={`webhook-delete-${w.id}`}><Trash2 size={15} /></Button>
              </div>
              {expanded === w.id && (
                <div className="border-t border-border bg-background/50">
                  <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent Deliveries</div>
                  <Deliveries webhookId={w.id} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

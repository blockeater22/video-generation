import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Copy, Check, KeyRound } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import api from "@/lib/api";

const fmt = (s) => (s ? new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Never");

export default function ApiKeys() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [env, setEnv] = useState("live");
  const [newKey, setNewKey] = useState(null);
  const [copied, setCopied] = useState(false);

  const { data, isLoading } = useQuery({ queryKey: ["api-keys"], queryFn: api.listApiKeys });
  const create = useMutation({
    mutationFn: api.createApiKey,
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["api-keys"] }); setNewKey(d.key); setName(""); },
  });
  const del = useMutation({
    mutationFn: api.deleteApiKey,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["api-keys"] }); toast.success("Key revoked"); },
  });

  const copy = () => { navigator.clipboard.writeText(newKey); setCopied(true); toast.success("Copied"); setTimeout(() => setCopied(false), 1500); };
  const closeDialog = () => { setOpen(false); setNewKey(null); setCopied(false); };

  return (
    <div className="space-y-6" data-testid="apikeys-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground mt-1">Authenticate requests to the developer API.</p>
        </div>
        <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : closeDialog())}>
          <DialogTrigger asChild>
            <Button data-testid="apikey-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> New Key</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><KeyRound size={18} className="text-accent" /> {newKey ? "Save your key" : "Create API Key"}</DialogTitle></DialogHeader>
            {newKey ? (
              <div className="space-y-3 py-2">
                <p className="text-sm text-muted-foreground">Copy it now — you won't be able to see it again.</p>
                <div className="flex items-center gap-2 bg-secondary border border-border rounded-md p-3">
                  <code className="text-sm font-mono flex-1 break-all" data-testid="apikey-value">{newKey}</code>
                  <Button size="sm" variant="ghost" onClick={copy} data-testid="apikey-copy">{copied ? <Check size={15} className="text-emerald-400" /> : <Copy size={15} />}</Button>
                </div>
                <Button onClick={closeDialog} className="w-full bg-accent text-white hover:bg-accent/90">Done</Button>
              </div>
            ) : (
              <>
                <div className="space-y-4 py-2">
                  <div><Label className="mb-1.5 block">Name</Label><Input data-testid="apikey-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Production server" /></div>
                  <div>
                    <Label className="mb-1.5 block">Environment</Label>
                    <Select value={env} onValueChange={setEnv}>
                      <SelectTrigger data-testid="apikey-env"><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="live">Live (ap_live_)</SelectItem><SelectItem value="test">Test (ap_test_)</SelectItem></SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button data-testid="apikey-submit" disabled={!name || create.isPending} onClick={() => create.mutate({ name, environment: env })} className="bg-accent text-white hover:bg-accent/90">Generate Key</Button>
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : data.length === 0 ? (
        <div className="border border-dashed border-border rounded-md py-16 text-center">
          <KeyRound className="mx-auto text-muted-foreground mb-3" size={28} />
          <p className="text-muted-foreground">No API keys yet.</p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-md divide-y divide-border" data-testid="apikeys-list">
          {data.map((k) => (
            <div key={k.id} className="flex items-center gap-4 p-4">
              <div className="flex-1 min-w-0">
                <div className="font-medium flex items-center gap-2">{k.name}
                  <Badge variant="outline" className="text-[10px] font-mono">{k.key_prefix.startsWith("ap_test") ? "TEST" : "LIVE"}</Badge>
                </div>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">{k.key_prefix}•••••••• · created {fmt(k.created_at)} · last used {fmt(k.last_used_at)}</div>
              </div>
              <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400" onClick={() => del.mutate(k.id)} data-testid={`apikey-delete-${k.id}`}><Trash2 size={15} /></Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

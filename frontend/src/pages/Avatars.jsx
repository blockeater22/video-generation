import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

const SAMPLE_THUMBS = [
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&q=80",
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&q=80",
  "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&q=80",
];

export default function Avatars() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [thumb, setThumb] = useState("");

  const { data, isLoading } = useQuery({ queryKey: ["avatars"], queryFn: api.listAvatars, refetchInterval: 4000 });

  const create = useMutation({
    mutationFn: api.createAvatar,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["avatars"] });
      toast.success("Avatar is processing");
      setOpen(false); setName(""); setThumb("");
    },
  });
  const del = useMutation({
    mutationFn: api.deleteAvatar,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["avatars"] }); toast.success("Avatar deleted"); },
  });

  return (
    <div className="space-y-6" data-testid="avatars-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Avatars</h1>
          <p className="text-muted-foreground mt-1">Your custom avatars and platform presenters.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="avatars-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> New Avatar</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><Sparkles size={18} className="text-accent" /> Create Avatar</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label className="mb-1.5 block">Avatar name</Label>
                <Input data-testid="avatar-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My Presenter" />
              </div>
              <div>
                <Label className="mb-1.5 block">Source image URL <span className="text-muted-foreground">(optional)</span></Label>
                <Input data-testid="avatar-thumb-input" value={thumb} onChange={(e) => setThumb(e.target.value)} placeholder="https://..." />
                <div className="flex gap-2 mt-2">
                  {SAMPLE_THUMBS.map((t) => (
                    <button key={t} onClick={() => setThumb(t)} className={`h-12 w-12 rounded overflow-hidden border-2 ${thumb === t ? "border-accent" : "border-transparent"}`}>
                      <img src={t} alt="" className="h-full w-full object-cover" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                data-testid="avatar-submit-btn"
                disabled={!name || create.isPending}
                onClick={() => create.mutate({ name, source_type: "image", thumbnail_url: thumb || undefined })}
                className="bg-accent text-white hover:bg-accent/90"
              >
                {create.isPending ? "Creating..." : "Create Avatar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-56" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="avatars-grid">
          {data.map((a) => (
            <div key={a.id} className="bg-card border border-border rounded-md overflow-hidden group hover:scale-[1.02] transition-transform duration-200">
              <div className="aspect-[3/4] bg-muted relative overflow-hidden">
                {a.thumbnail_url && <img src={a.thumbnail_url} alt={a.name} className="h-full w-full object-cover" />}
                <div className="absolute top-2 left-2"><StatusBadge status={a.status} /></div>
                {a.is_stock && <Badge className="absolute top-2 right-2 bg-black/70 text-white border-0 text-[10px]">STOCK</Badge>}
              </div>
              <div className="p-3 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{a.name}</div>
                  <div className="text-xs text-muted-foreground capitalize">{a.source_type}</div>
                </div>
                {!a.is_stock && (
                  <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400 h-7 w-7 p-0" onClick={() => del.mutate(a.id)} data-testid={`avatar-delete-${a.id}`}>
                    <Trash2 size={14} />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

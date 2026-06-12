import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, FolderKanban } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import api from "@/lib/api";

export default function Projects() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  const { data, isLoading } = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });
  const create = useMutation({
    mutationFn: api.createProject,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); toast.success("Project created"); setOpen(false); setName(""); setDesc(""); },
  });
  const del = useMutation({
    mutationFn: api.deleteProject,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); toast.success("Project deleted"); },
  });

  return (
    <div className="space-y-6" data-testid="projects-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground mt-1">Organize your videos into workspaces.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="projects-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> New Project</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display">Create Project</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div><Label className="mb-1.5 block">Name</Label><Input data-testid="project-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Marketing Campaign" /></div>
              <div><Label className="mb-1.5 block">Description</Label><Textarea value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Optional" className="resize-none" /></div>
            </div>
            <DialogFooter>
              <Button data-testid="project-submit-btn" disabled={!name || create.isPending} onClick={() => create.mutate({ name, description: desc })} className="bg-accent text-white hover:bg-accent/90">Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32" />)}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="projects-grid">
          {data.map((p) => (
            <div key={p.id} className="bg-card border border-border rounded-md p-5 group">
              <div className="flex items-start justify-between">
                <div className="h-10 w-10 rounded-md bg-secondary flex items-center justify-center mb-3"><FolderKanban size={18} className="text-accent" /></div>
                <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400 h-7 w-7 p-0 opacity-0 group-hover:opacity-100" onClick={() => del.mutate(p.id)} data-testid={`project-delete-${p.id}`}>
                  <Trash2 size={14} />
                </Button>
              </div>
              <div className="font-display font-semibold text-lg tracking-tight">{p.name}</div>
              <p className="text-sm text-muted-foreground mt-1">{p.description || "No description"}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

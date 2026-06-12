import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Download, RotateCw, Film } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

const fmtDate = (s) => new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });

export default function Videos() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [preview, setPreview] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["videos"],
    queryFn: () => api.listVideos(),
    refetchInterval: 4000,
  });

  const del = useMutation({
    mutationFn: api.deleteVideo,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["videos"] }); toast.success("Video deleted"); },
  });
  const retry = useMutation({
    mutationFn: api.retryVideo,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["videos"] }); toast.success("Re-queued"); },
  });

  const items = (data?.items || []).filter((v) => filter === "all" || v.status === filter);

  return (
    <div className="space-y-6" data-testid="videos-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Videos</h1>
          <p className="text-muted-foreground mt-1">Manage and download your generated videos.</p>
        </div>
        <Button data-testid="videos-create-btn" onClick={() => navigate("/editor")} className="bg-accent text-white hover:bg-accent/90 gap-2">
          <Plus size={16} /> Create Video
        </Button>
      </div>

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="bg-secondary">
          {["all", "completed", "processing", "queued", "failed"].map((s) => (
            <TabsTrigger key={s} value={s} data-testid={`videos-filter-${s}`} className="capitalize">{s}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-64" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-border rounded-md py-20 text-center">
          <Film className="mx-auto text-muted-foreground mb-3" size={32} />
          <p className="text-muted-foreground">No videos here yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="videos-grid">
          {items.map((v) => (
            <div key={v.id} className="bg-card border border-border rounded-md overflow-hidden group">
              <div
                className="aspect-video bg-muted relative cursor-pointer overflow-hidden"
                onClick={() => v.status === "completed" && setPreview(v)}
              >
                {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="h-full w-full object-cover group-hover:scale-[1.03] transition-transform duration-300" />}
                <div className="absolute top-2 left-2"><StatusBadge status={v.status} /></div>
                {v.duration_seconds && (
                  <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs font-mono px-1.5 py-0.5 rounded">
                    {v.duration_seconds}s
                  </div>
                )}
              </div>
              <div className="p-4">
                <div className="font-medium truncate">{v.title}</div>
                <div className="text-xs text-muted-foreground font-mono mt-1">{v.resolution} · {v.aspect_ratio} · {fmtDate(v.created_at)}</div>
                {v.status === "failed" && v.error_message && (
                  <p className="text-xs text-red-400 mt-1.5 line-clamp-2" data-testid={`video-error-${v.id}`}>{v.error_message}</p>
                )}
                <div className="flex items-center gap-2 mt-3">
                  {v.status === "completed" && (
                    <Button size="sm" variant="secondary" className="gap-1.5 flex-1" onClick={() => window.open(v.output_url, "_blank")} data-testid={`video-download-${v.id}`}>
                      <Download size={14} /> Download
                    </Button>
                  )}
                  {v.status === "failed" && (
                    <Button size="sm" variant="secondary" className="gap-1.5 flex-1" onClick={() => retry.mutate(v.id)} data-testid={`video-retry-${v.id}`}>
                      <RotateCw size={14} /> Retry
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400" onClick={() => del.mutate(v.id)} data-testid={`video-delete-${v.id}`}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-3xl bg-card border-border">
          <DialogHeader><DialogTitle className="font-display">{preview?.title}</DialogTitle></DialogHeader>
          {preview && (
            <video src={preview.output_url} controls autoPlay className="w-full rounded-md" data-testid="video-player" />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

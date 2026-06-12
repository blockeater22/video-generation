import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ArrowLeft, Zap, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

const RES = ["720p", "1080p", "4k"];
const RATIOS = ["16:9", "9:16", "1:1"];
const BG_COLORS = ["#0A0A0A", "#FFFFFF", "#EF4444", "#1E3A8A", "#065F46", "#7C3AED"];

export default function Editor() {
  const navigate = useNavigate();
  const { id } = useParams();
  const qc = useQueryClient();

  const { data: avatars } = useQuery({ queryKey: ["avatars"], queryFn: api.listAvatars });
  const { data: voices } = useQuery({ queryKey: ["voices"], queryFn: api.listVoices });

  const [title, setTitle] = useState("Untitled Video");
  const [avatarId, setAvatarId] = useState(null);
  const [voiceId, setVoiceId] = useState(null);
  const [script, setScript] = useState("");
  const [resolution, setResolution] = useState("1080p");
  const [ratio, setRatio] = useState("16:9");
  const [bg, setBg] = useState("#0A0A0A");
  const [captions, setCaptions] = useState(true);
  const [speed, setSpeed] = useState([1]);
  const [jobId, setJobId] = useState(id || null);

  useEffect(() => {
    if (avatars?.length && !avatarId) setAvatarId(avatars.find((a) => a.status === "ready")?.id || avatars[0].id);
  }, [avatars, avatarId]);
  useEffect(() => {
    if (voices?.length && !voiceId) setVoiceId(voices[0].id);
  }, [voices, voiceId]);

  const { data: job } = useQuery({
    queryKey: ["video", jobId],
    queryFn: () => api.getVideo(jobId),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 3000;
    },
  });

  const create = useMutation({
    mutationFn: api.createVideo,
    onSuccess: (v) => {
      setJobId(v.id);
      qc.invalidateQueries({ queryKey: ["videos"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Generation started");
    },
    onError: () => toast.error("Failed to start generation"),
  });

  const selectedAvatar = avatars?.find((a) => a.id === avatarId);

  const generate = () => {
    if (!avatarId || !voiceId) return toast.error("Select an avatar and voice");
    if (!script.trim()) return toast.error("Write a script first");
    create.mutate({
      avatar_id: avatarId, voice_id: voiceId, title, script,
      resolution, aspect_ratio: ratio, background_type: "solid", background_value: bg,
      settings: { caption_enabled: captions, speed: speed[0] },
    });
  };

  return (
    <div className="dark min-h-screen bg-background flex flex-col" data-testid="editor-page">
      {/* Top bar */}
      <header className="h-16 border-b border-border flex items-center justify-between px-4 md:px-6 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Button variant="ghost" size="sm" onClick={() => navigate("/videos")} className="gap-1.5 text-muted-foreground" data-testid="editor-back-btn">
            <ArrowLeft size={16} /> Back
          </Button>
          <div className="h-5 w-px bg-border" />
          <Input
            data-testid="editor-title-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="border-0 bg-transparent font-display font-semibold text-base focus-visible:ring-0 px-0 w-48 md:w-72"
          />
        </div>
        <Button
          data-testid="editor-generate-btn"
          onClick={generate}
          disabled={create.isPending}
          className="bg-accent text-white hover:bg-accent/90 font-semibold gap-2 shadow-[0_0_18px_rgba(239,68,68,0.3)]"
        >
          <Zap size={16} /> {create.isPending ? "Starting..." : "Generate"}
        </Button>
      </header>

      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* LEFT: Avatar & Voice */}
        <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-border overflow-y-auto p-4 space-y-6" data-testid="editor-left-panel">
          <div>
            <h4 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground mb-3">Avatar</h4>
            <div className="grid grid-cols-3 gap-2">
              {avatars?.map((a) => (
                <button
                  key={a.id}
                  data-testid={`editor-avatar-${a.id}`}
                  onClick={() => setAvatarId(a.id)}
                  className={`aspect-[3/4] rounded-md overflow-hidden border-2 transition-all ${avatarId === a.id ? "border-accent" : "border-transparent hover:border-border"}`}
                >
                  <img src={a.thumbnail_url} alt={a.name} className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground mb-3">Voice</h4>
            <Select value={voiceId || ""} onValueChange={setVoiceId}>
              <SelectTrigger data-testid="editor-voice-select"><SelectValue placeholder="Select voice" /></SelectTrigger>
              <SelectContent>
                {voices?.map((v) => <SelectItem key={v.id} value={v.id}>{v.name} · {v.language} · {v.engine}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </aside>

        {/* CENTER: Preview + script */}
        <section className="flex-1 flex flex-col bg-muted/20 p-4 md:p-6 overflow-y-auto" data-testid="editor-center">
          <div className="flex-1 flex items-center justify-center mb-4 min-h-[260px]">
            <div className="w-full max-w-2xl aspect-video rounded-md border border-border bg-card overflow-hidden relative flex items-center justify-center">
              {job?.status === "completed" ? (
                <video src={job.output_url} controls autoPlay className="h-full w-full object-contain bg-black" data-testid="editor-preview-video" />
              ) : jobId && job ? (
                <div className="text-center">
                  {job.status === "failed" ? (
                    <StatusBadge status="failed" />
                  ) : (
                    <>
                      <Loader2 className="mx-auto animate-spin text-accent mb-3" size={32} />
                      <div className="mb-2"><StatusBadge status={job.status} /></div>
                      <p className="text-sm text-muted-foreground">Rendering your avatar video…</p>
                    </>
                  )}
                </div>
              ) : selectedAvatar ? (
                <img src={selectedAvatar.thumbnail_url} alt="" className="h-full w-full object-cover opacity-60" style={{ background: bg }} />
              ) : (
                <p className="text-muted-foreground text-sm">Select an avatar to preview</p>
              )}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Script</Label>
              <span className="text-xs text-muted-foreground font-mono" data-testid="editor-char-count">{script.length} / 10000</span>
            </div>
            <Textarea
              data-testid="editor-script-input"
              value={script}
              onChange={(e) => setScript(e.target.value.slice(0, 10000))}
              placeholder="Type what your avatar should say…"
              className="min-h-[140px] resize-none bg-background border-input font-body text-base leading-relaxed"
            />
          </div>
        </section>

        {/* RIGHT: Settings */}
        <aside className="w-full lg:w-72 border-t lg:border-t-0 lg:border-l border-border overflow-y-auto p-4 space-y-6" data-testid="editor-right-panel">
          <div>
            <h4 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground mb-3">Resolution</h4>
            <div className="flex gap-2">
              {RES.map((r) => (
                <button key={r} data-testid={`editor-res-${r}`} onClick={() => setResolution(r)}
                  className={`flex-1 py-1.5 rounded-md text-sm font-medium border transition-all ${resolution === r ? "border-accent bg-accent/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}>
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground mb-3">Aspect Ratio</h4>
            <div className="flex gap-2">
              {RATIOS.map((r) => (
                <button key={r} onClick={() => setRatio(r)}
                  className={`flex-1 py-1.5 rounded-md text-sm font-mono border transition-all ${ratio === r ? "border-accent bg-accent/10 text-foreground" : "border-border text-muted-foreground hover:text-foreground"}`}>
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground mb-3">Background</h4>
            <div className="flex gap-2 flex-wrap">
              {BG_COLORS.map((c) => (
                <button key={c} onClick={() => setBg(c)}
                  className={`h-8 w-8 rounded-md border-2 transition-all ${bg === c ? "border-accent scale-110" : "border-border"}`}
                  style={{ background: c }}>
                  {bg === c && <Check size={14} className="mx-auto" style={{ color: c === "#FFFFFF" ? "#000" : "#fff" }} />}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <Label className="text-sm">Captions</Label>
            <Switch checked={captions} onCheckedChange={setCaptions} data-testid="editor-captions-switch" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-sm">Speed</Label>
              <span className="text-xs font-mono text-muted-foreground">{speed[0].toFixed(1)}x</span>
            </div>
            <Slider value={speed} onValueChange={setSpeed} min={0.5} max={2} step={0.1} data-testid="editor-speed-slider" />
          </div>
        </aside>
      </div>
    </div>
  );
}

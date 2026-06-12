import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, AudioLines, Mic, Play, Square, Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import api from "@/lib/api";

const LANGS = { en: "English", es: "Spanish", ja: "Japanese", fr: "French", de: "German" };

const OPENAI_VOICES = [
  { id: "alloy", label: "Alloy — Neutral, balanced" },
  { id: "ash", label: "Ash — Clear, articulate" },
  { id: "coral", label: "Coral — Warm, friendly" },
  { id: "echo", label: "Echo — Smooth, calm" },
  { id: "fable", label: "Fable — Expressive, storytelling" },
  { id: "nova", label: "Nova — Energetic, upbeat" },
  { id: "onyx", label: "Onyx — Deep, authoritative" },
  { id: "sage", label: "Sage — Wise, measured" },
  { id: "shimmer", label: "Shimmer — Bright, cheerful" },
];

export default function Voices() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [gender, setGender] = useState("female");
  const [openaiVoice, setOpenaiVoice] = useState("alloy");
  const [playing, setPlaying] = useState(null); // voiceId | `${id}:loading`
  const audioRef = useRef(null);

  const { data, isLoading } = useQuery({ queryKey: ["voices"], queryFn: api.listVoices });

  const create = useMutation({
    mutationFn: api.createVoice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["voices"] }); toast.success("Voice created"); setOpen(false); setName(""); },
  });
  const del = useMutation({
    mutationFn: api.deleteVoice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["voices"] }); toast.success("Voice deleted"); },
  });

  const stopAudio = () => {
    if (audioRef.current) audioRef.current.pause();
    setPlaying(null);
  };

  const playPreview = async (v) => {
    if (playing === v.id) return stopAudio();
    try {
      stopAudio();
      setPlaying(`${v.id}:loading`);
      let url = v.sample_audio_url;
      if (!url) {
        const res = await api.previewVoice(v.id);
        url = res.sample_audio_url;
        qc.invalidateQueries({ queryKey: ["voices"] });
      }
      const a = new Audio(url);
      audioRef.current = a;
      a.onended = () => setPlaying(null);
      await a.play();
      setPlaying(v.id);
    } catch {
      toast.error("Voice preview failed");
      setPlaying(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="voices-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Voices</h1>
          <p className="text-muted-foreground mt-1">Real neural TTS voices for your videos — press play to hear them.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="voices-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> New Voice</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><Mic size={18} className="text-accent" /> Create a Voice</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label className="mb-1.5 block">Voice name</Label>
                <Input data-testid="voice-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My Brand Voice" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="mb-1.5 block">Language</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger data-testid="voice-lang-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{Object.entries(LANGS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="mb-1.5 block">Gender</Label>
                  <Select value={gender} onValueChange={setGender}>
                    <SelectTrigger data-testid="voice-gender-select"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="female">Female</SelectItem><SelectItem value="male">Male</SelectItem></SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label className="mb-1.5 block">Voice style</Label>
                <Select value={openaiVoice} onValueChange={setOpenaiVoice}>
                  <SelectTrigger data-testid="voice-style-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {OPENAI_VOICES.map((v) => <SelectItem key={v.id} value={v.id}>{v.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1.5">Powered by neural TTS — every video speaks with real AI speech.</p>
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="voice-submit-btn" disabled={!name || create.isPending}
                onClick={() => create.mutate({ name, language, gender, engine: "openai_tts", openai_voice: openaiVoice })}
                className="bg-accent text-white hover:bg-accent/90">
                {create.isPending ? "Creating..." : "Create Voice"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="voices-grid">
          {data.map((v) => (
            <div key={v.id} className="bg-card border border-border rounded-md p-4 flex items-center gap-4">
              <button
                data-testid={`voice-preview-${v.id}`}
                onClick={() => playPreview(v)}
                className="h-12 w-12 rounded-md bg-secondary hover:bg-accent/20 flex items-center justify-center flex-shrink-0 transition-colors"
                title="Play preview"
              >
                {playing === `${v.id}:loading` ? (
                  <Loader2 size={20} className="text-accent animate-spin" />
                ) : playing === v.id ? (
                  <Square size={16} className="text-accent" />
                ) : (
                  <Play size={18} className="text-accent" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{v.name}</div>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">
                  {LANGS[v.language] || v.language} · {v.gender} · {v.openai_voice || v.engine}
                </div>
              </div>
              {v.is_stock ? (
                <Badge className="bg-secondary text-muted-foreground border-0 text-[10px]">STOCK</Badge>
              ) : (
                <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400 h-8 w-8 p-0" onClick={() => del.mutate(v.id)} data-testid={`voice-delete-${v.id}`}>
                  <Trash2 size={14} />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

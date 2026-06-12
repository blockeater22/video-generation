import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, AudioLines, Mic } from "lucide-react";
import { useState } from "react";
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

export default function Voices() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [gender, setGender] = useState("female");
  const [engine, setEngine] = useState("xtts");

  const { data, isLoading } = useQuery({ queryKey: ["voices"], queryFn: api.listVoices });

  const create = useMutation({
    mutationFn: api.createVoice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["voices"] }); toast.success("Voice cloned"); setOpen(false); setName(""); },
  });
  const del = useMutation({
    mutationFn: api.deleteVoice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["voices"] }); toast.success("Voice deleted"); },
  });

  return (
    <div className="space-y-6" data-testid="voices-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Voices</h1>
          <p className="text-muted-foreground mt-1">Cloned and stock voices for your videos.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="voices-create-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> Clone Voice</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><Mic size={18} className="text-accent" /> Clone a Voice</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label className="mb-1.5 block">Voice name</Label>
                <Input data-testid="voice-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. My Voice" />
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
                <Label className="mb-1.5 block">Engine</Label>
                <Select value={engine} onValueChange={setEngine}>
                  <SelectTrigger data-testid="voice-engine-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="xtts">XTTS v2</SelectItem>
                    <SelectItem value="f5-tts">F5-TTS</SelectItem>
                    <SelectItem value="elevenlabs">ElevenLabs</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="voice-submit-btn" disabled={!name || create.isPending} onClick={() => create.mutate({ name, language, gender, engine })} className="bg-accent text-white hover:bg-accent/90">
                {create.isPending ? "Cloning..." : "Clone Voice"}
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
              <div className="h-12 w-12 rounded-md bg-secondary flex items-center justify-center flex-shrink-0">
                <AudioLines size={20} className="text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{v.name}</div>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">
                  {LANGS[v.language] || v.language} · {v.gender} · {v.engine}
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

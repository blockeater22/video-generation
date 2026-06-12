import { useState } from "react";
import { Terminal, Copy, Check, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

const BASE = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;

const SNIPPETS = {
  curl: `curl -X POST ${BASE}/videos \\
  -H "Authorization: Bearer ap_live_xxx" \\
  -H "Content-Type: application/json" \\
  -d '{
    "avatar_id": "avt_abc123",
    "voice_id": "vce_def456",
    "script": "Hello from AvatarPlatform!"
  }'`,
  python: `from avatarplatform import AvatarPlatform

client = AvatarPlatform(api_key="ap_live_xxx")

video = client.videos.create(
    avatar_id="avt_abc123",
    voice_id="vce_def456",
    script="Hello from AvatarPlatform!",
)

# Poll until rendered
video = client.videos.wait(video.id)
print(video.output_url)`,
  js: `import { AvatarPlatform } from "avatarplatform";

const client = new AvatarPlatform("ap_live_xxx");

const video = await client.videos.create({
  avatar_id: "avt_abc123",
  voice_id: "vce_def456",
  script: "Hello from AvatarPlatform!",
});

const done = await client.videos.wait(video.id);
console.log(done.output_url);`,
};

const ENDPOINTS = [
  { m: "POST", p: "/v1/videos", d: "Create a video generation job" },
  { m: "GET", p: "/v1/videos", d: "List videos" },
  { m: "GET", p: "/v1/videos/{id}", d: "Retrieve a video" },
  { m: "GET", p: "/v1/avatars", d: "List avatars (yours + stock)" },
  { m: "GET", p: "/v1/voices", d: "List voices (yours + stock)" },
];

const METHOD_CLS = { GET: "text-emerald-400 border-emerald-400/30", POST: "text-blue-400 border-blue-400/30" };

function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return (
    <div className="relative">
      <button onClick={copy} className="absolute top-3 right-3 text-muted-foreground hover:text-foreground" data-testid="copy-snippet">
        {copied ? <Check size={15} className="text-emerald-400" /> : <Copy size={15} />}
      </button>
      <pre className="bg-background border border-border rounded-md p-4 overflow-x-auto text-sm font-mono leading-relaxed"><code>{code}</code></pre>
    </div>
  );
}

export default function Developer() {
  return (
    <div className="space-y-8 max-w-4xl" data-testid="developer-page">
      <div>
        <h1 className="font-display text-4xl font-bold tracking-tight">Developer API</h1>
        <p className="text-muted-foreground mt-1">Generate videos programmatically with a first-class REST API.</p>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center gap-2 mb-2"><Terminal size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Base URL</h3></div>
        <code className="text-sm font-mono text-muted-foreground break-all">{BASE}</code>
        <p className="text-sm text-muted-foreground mt-3">Authenticate every request with your API key in the <code className="font-mono text-foreground">Authorization</code> header. Create one in the API Keys page.</p>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center gap-2 mb-4"><BookOpen size={18} className="text-accent" /><h3 className="font-display text-lg font-semibold">Quickstart</h3></div>
        <Tabs defaultValue="curl">
          <TabsList className="bg-secondary">
            <TabsTrigger value="curl" data-testid="snippet-curl">cURL</TabsTrigger>
            <TabsTrigger value="python" data-testid="snippet-python">Python</TabsTrigger>
            <TabsTrigger value="js" data-testid="snippet-js">JavaScript</TabsTrigger>
          </TabsList>
          <TabsContent value="curl" className="mt-4"><CodeBlock code={SNIPPETS.curl} /></TabsContent>
          <TabsContent value="python" className="mt-4"><CodeBlock code={SNIPPETS.python} /></TabsContent>
          <TabsContent value="js" className="mt-4"><CodeBlock code={SNIPPETS.js} /></TabsContent>
        </Tabs>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <h3 className="font-display text-lg font-semibold mb-4">Endpoints</h3>
        <div className="divide-y divide-border" data-testid="endpoints-list">
          {ENDPOINTS.map((e) => (
            <div key={e.p} className="flex items-center gap-4 py-3">
              <Badge variant="outline" className={`font-mono text-xs w-14 justify-center ${METHOD_CLS[e.m]}`}>{e.m}</Badge>
              <code className="font-mono text-sm flex-1">{e.p}</code>
              <span className="text-sm text-muted-foreground hidden sm:block">{e.d}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-md p-6">
        <h3 className="font-display text-lg font-semibold mb-2">Webhooks</h3>
        <p className="text-sm text-muted-foreground">Register a webhook to receive <code className="font-mono text-foreground">video.completed</code> and <code className="font-mono text-foreground">video.failed</code> events. Each payload is signed with HMAC-SHA256 in the <code className="font-mono text-foreground">X-AvatarPlatform-Signature</code> header.</p>
      </div>
    </div>
  );
}

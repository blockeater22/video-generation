import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, ResponsiveContainer, XAxis, Tooltip, Cell } from "recharts";
import { Plus, Clapperboard, Users, AudioLines, ArrowUpRight, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import StatusBadge from "@/components/StatusBadge";
import api from "@/lib/api";

const Stat = ({ label, value, icon: Icon, testid }) => (
  <div data-testid={testid} className="bg-card border border-border rounded-md p-5">
    <div className="flex items-center justify-between mb-3">
      <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">{label}</span>
      <Icon size={16} className="text-muted-foreground" />
    </div>
    <div className="font-display text-3xl font-bold tracking-tight">{value}</div>
  </div>
);

export default function Dashboard() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboardStats,
    refetchInterval: 4000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const org = data.org;
  const pct = Math.min(100, Math.round((org.credits_used / org.credits_limit) * 100));
  const chart = data.usage_last_30_days.map((d) => ({ ...d, day: d.date.slice(5) }));

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Studio Overview</h1>
          <p className="text-muted-foreground mt-1">Welcome back to {org.name}.</p>
        </div>
        <Button
          data-testid="dashboard-create-video-btn"
          onClick={() => navigate("/editor")}
          className="bg-accent text-white hover:bg-accent/90 gap-2 shadow-[0_0_18px_rgba(239,68,68,0.25)]"
        >
          <Plus size={16} /> Create Video
        </Button>
      </div>

      {/* Credits */}
      <div data-testid="dashboard-credits" className="bg-card border border-border rounded-md p-6">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">Monthly Credits</span>
            <div className="font-display text-2xl font-bold tracking-tight mt-1">
              <span className="font-mono">{org.credits_used}</span>
              <span className="text-muted-foreground"> / {org.credits_limit} videos</span>
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-3xl font-bold text-accent">{org.credits_limit - org.credits_used}</div>
            <div className="text-xs text-muted-foreground">remaining</div>
          </div>
        </div>
        <Progress value={pct} className="h-2 [&>div]:bg-accent" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat testid="stat-videos" label="Total Videos" value={data.totals.videos} icon={Clapperboard} />
        <Stat testid="stat-completed" label="Completed" value={data.counts.completed} icon={Play} />
        <Stat testid="stat-avatars" label="Avatars" value={data.totals.avatars} icon={Users} />
        <Stat testid="stat-voices" label="Voices" value={data.totals.voices} icon={AudioLines} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Usage chart */}
        <div className="lg:col-span-2 bg-card border border-border rounded-md p-6">
          <h3 className="font-display text-lg font-semibold tracking-tight mb-1">Generation Activity</h3>
          <p className="text-xs text-muted-foreground mb-6">Videos created · last 30 days</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chart}>
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "hsl(0 0% 50%)" }} interval={4} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ fill: "hsl(0 0% 100% / 0.04)" }}
                contentStyle={{ background: "hsl(0 0% 8%)", border: "1px solid hsl(0 0% 18%)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "hsl(0 0% 70%)" }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {chart.map((_, i) => <Cell key={i} fill="hsl(0 84% 60%)" />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Recent videos */}
        <div className="bg-card border border-border rounded-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-lg font-semibold tracking-tight">Recent Videos</h3>
            <button onClick={() => navigate("/videos")} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
              View all <ArrowUpRight size={12} />
            </button>
          </div>
          <div className="space-y-3" data-testid="dashboard-recent-videos">
            {data.recent_videos.length === 0 && (
              <p className="text-sm text-muted-foreground py-8 text-center">No videos yet. Create your first one!</p>
            )}
            {data.recent_videos.map((v) => (
              <div key={v.id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                <div className="h-10 w-16 rounded bg-muted overflow-hidden flex-shrink-0">
                  {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="h-full w-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{v.title}</div>
                  <div className="text-xs text-muted-foreground font-mono">{v.resolution}</div>
                </div>
                <StatusBadge status={v.status} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

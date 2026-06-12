import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Mail, UserCircle2 } from "lucide-react";
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

const ROLE_CLS = {
  owner: "text-accent border-accent/30 bg-accent/10",
  admin: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  member: "text-muted-foreground border-border bg-secondary",
  viewer: "text-muted-foreground border-border bg-secondary",
};

export default function Team() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");

  const { data: members, isLoading } = useQuery({ queryKey: ["members"], queryFn: api.listMembers });
  const { data: invites } = useQuery({ queryKey: ["invitations"], queryFn: api.listInvitations });

  const invite = useMutation({
    mutationFn: api.createInvitation,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["invitations"] }); toast.success("Invitation sent"); setOpen(false); setEmail(""); },
  });
  const delInvite = useMutation({
    mutationFn: api.deleteInvitation,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["invitations"] }); toast.success("Invitation revoked"); },
  });

  return (
    <div className="space-y-6" data-testid="team-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Team</h1>
          <p className="text-muted-foreground mt-1">Manage organization members and roles.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="team-invite-btn" className="bg-accent text-white hover:bg-accent/90 gap-2"><Plus size={16} /> Invite Member</Button>
          </DialogTrigger>
          <DialogContent className="bg-card border-border">
            <DialogHeader><DialogTitle className="font-display flex items-center gap-2"><Mail size={18} className="text-accent" /> Invite Member</DialogTitle></DialogHeader>
            <div className="space-y-4 py-2">
              <div><Label className="mb-1.5 block">Email</Label><Input data-testid="invite-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="colleague@company.com" /></div>
              <div>
                <Label className="mb-1.5 block">Role</Label>
                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger data-testid="invite-role"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="invite-submit" disabled={!email || invite.isPending} onClick={() => invite.mutate({ email, role })} className="bg-accent text-white hover:bg-accent/90">Send Invite</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Members</h3>
        {isLoading ? <Skeleton className="h-24" /> : (
          <div className="bg-card border border-border rounded-md divide-y divide-border" data-testid="members-list">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-4 p-4">
                <UserCircle2 size={32} className="text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{m.full_name || m.email}</div>
                  <div className="text-xs text-muted-foreground">{m.email}</div>
                </div>
                <Badge variant="outline" className={`capitalize ${ROLE_CLS[m.role] || ROLE_CLS.member}`}>{m.role}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>

      {invites?.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Pending Invitations</h3>
          <div className="bg-card border border-border rounded-md divide-y divide-border" data-testid="invites-list">
            {invites.map((i) => (
              <div key={i.id} className="flex items-center gap-4 p-4">
                <Mail size={20} className="text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm">{i.email}</div>
                  <div className="text-xs text-muted-foreground capitalize">{i.role} · pending</div>
                </div>
                <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-red-400" onClick={() => delInvite.mutate(i.id)} data-testid={`invite-delete-${i.id}`}><Trash2 size={15} /></Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

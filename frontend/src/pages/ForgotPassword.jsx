import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import AuthShell from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api, { formatApiError } from "@/lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.forgotPassword({ email });
      setSent(true);
      toast.success("If that email exists, a reset link was sent");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Reset password"
      subtitle="We'll email you a reset link."
      footer={<><Link to="/login" className="text-accent hover:underline">Back to sign in</Link></>}
    >
      {sent ? (
        <div className="bg-secondary border border-border rounded-md p-4 text-sm text-muted-foreground" data-testid="forgot-sent">
          Check your inbox (and the server console in this demo) for a reset link.
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          <div>
            <Label className="mb-1.5 block">Email</Label>
            <Input data-testid="forgot-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
          </div>
          <Button data-testid="forgot-submit" type="submit" disabled={loading} className="w-full bg-accent text-white hover:bg-accent/90 gap-2">
            {loading && <Loader2 size={16} className="animate-spin" />} Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

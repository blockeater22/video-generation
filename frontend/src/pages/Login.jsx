import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import AuthShell from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login({ email, password });
      toast.success("Welcome back");
      navigate("/");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Sign in"
      subtitle="Access your studio dashboard."
      footer={<>No account? <Link to="/register" className="text-accent hover:underline" data-testid="link-register">Create one</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <div>
          <Label className="mb-1.5 block">Email</Label>
          <Input data-testid="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <Label>Password</Label>
            <Link to="/forgot-password" className="text-xs text-muted-foreground hover:text-foreground" data-testid="link-forgot">Forgot?</Link>
          </div>
          <Input data-testid="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
        </div>
        <Button data-testid="login-submit" type="submit" disabled={loading} className="w-full bg-accent text-white hover:bg-accent/90 gap-2">
          {loading && <Loader2 size={16} className="animate-spin" />} Sign in
        </Button>
      </form>
      <div className="mt-4 text-xs text-muted-foreground bg-secondary border border-border rounded-md p-3 font-mono">
        Demo: admin@avatarplatform.io / Admin123!
      </div>
    </AuthShell>
  );
}

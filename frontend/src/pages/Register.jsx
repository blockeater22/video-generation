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

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({ full_name: fullName, email, password });
      toast.success("Account created");
      navigate("/");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Create account"
      subtitle="Start generating avatar videos in minutes."
      footer={<>Already have an account? <Link to="/login" className="text-accent hover:underline" data-testid="link-login">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <div>
          <Label className="mb-1.5 block">Full name</Label>
          <Input data-testid="register-name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" required />
        </div>
        <div>
          <Label className="mb-1.5 block">Email</Label>
          <Input data-testid="register-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
        </div>
        <div>
          <Label className="mb-1.5 block">Password</Label>
          <Input data-testid="register-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 6 characters" required minLength={6} />
        </div>
        <Button data-testid="register-submit" type="submit" disabled={loading} className="w-full bg-accent text-white hover:bg-accent/90 gap-2">
          {loading && <Loader2 size={16} className="animate-spin" />} Create account
        </Button>
      </form>
    </AuthShell>
  );
}

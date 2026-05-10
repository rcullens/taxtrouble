import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ArrowRight, Buildings } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back.");
      const dest = loc.state?.from || "/dashboard";
      nav(dest);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-inverse text-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-10" />
        <Link to="/" className="flex items-center gap-2.5 relative">
          <div className="w-8 h-8 bg-white flex items-center justify-center">
            <Buildings size={18} weight="fill" color="#09090B" />
          </div>
          <span className="font-display text-lg font-semibold">LIEN/TX</span>
        </Link>
        <div className="relative">
          <span className="overline" style={{ color: "rgba(255,255,255,0.6)" }}>
            Property intelligence
          </span>
          <h2 className="font-display text-5xl font-semibold tracking-tighter mt-3 leading-[0.95]">
            Texas tax sales,
            <br />
            decoded.
          </h2>
          <p className="text-sm text-white/60 mt-6 max-w-sm">
            36+ real distressed properties pre-indexed across McLennan, Hill, and Bosque counties. Plus on-demand scrapers for any Texas county.
          </p>
        </div>
        <div className="relative font-mono text-xs text-white/40">
          tx.lien.intel / authenticated session
        </div>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="login-form">
          <div>
            <span className="overline">Sign in</span>
            <h1 className="font-display text-3xl font-semibold tracking-tight mt-2">
              Welcome back.
            </h1>
            <p className="text-sm text-ink-secondary mt-1">
              Continue tracking distressed Texas properties.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="overline block mb-2">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="swiss-input"
                placeholder="you@example.com"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <label className="overline block mb-2">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="swiss-input"
                placeholder="••••••••"
                data-testid="login-password-input"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="btn-primary w-full flex items-center justify-center gap-2"
            data-testid="login-submit-btn"
          >
            {busy ? "Signing in..." : <>Sign in <ArrowRight size={16} weight="bold" /></>}
          </button>

          <p className="text-sm text-ink-secondary text-center">
            No account?{" "}
            <Link to="/register" className="text-brand font-medium hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

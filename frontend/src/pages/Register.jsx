import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ArrowRight, Buildings } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }
    setBusy(true);
    try {
      await register(form.email, form.password, form.name);
      toast.success(`Welcome, ${form.name}.`);
      nav("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed");
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
            Free account
          </span>
          <h2 className="font-display text-5xl font-semibold tracking-tighter mt-3 leading-[0.95]">
            Start tracking
            <br />
            in minutes.
          </h2>
          <ul className="text-sm text-white/70 mt-6 space-y-2 max-w-sm">
            <li>· Save unlimited search filters</li>
            <li>· AI investment scoring on demand</li>
            <li>· CSV exports of filtered results</li>
            <li>· On-demand scraping of any TX county</li>
          </ul>
        </div>
        <div className="relative font-mono text-xs text-white/40">
          tx.lien.intel / new account
        </div>
      </div>

      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="register-form">
          <div>
            <span className="overline">Create account</span>
            <h1 className="font-display text-3xl font-semibold tracking-tight mt-2">
              Get started.
            </h1>
            <p className="text-sm text-ink-secondary mt-1">No credit card required.</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="overline block mb-2">Name</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="swiss-input"
                placeholder="Your name"
                data-testid="register-name-input"
              />
            </div>
            <div>
              <label className="overline block mb-2">Email</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="swiss-input"
                placeholder="you@example.com"
                data-testid="register-email-input"
              />
            </div>
            <div>
              <label className="overline block mb-2">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="swiss-input"
                placeholder="At least 6 characters"
                data-testid="register-password-input"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="btn-primary w-full flex items-center justify-center gap-2"
            data-testid="register-submit-btn"
          >
            {busy ? "Creating account..." : <>Create account <ArrowRight size={16} weight="bold" /></>}
          </button>

          <p className="text-sm text-ink-secondary text-center">
            Already have an account?{" "}
            <Link to="/login" className="text-brand font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}

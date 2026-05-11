import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Buildings, SignOut, User as UserIcon } from "@phosphor-icons/react";

export default function Header() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();

  const navItems = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/leaderboard", label: "Leaderboard" },
    { to: "/scrape", label: "Scrape" },
    ...(user ? [{ to: "/saved", label: "Saved Searches" }] : []),
  ];

  return (
    <header className="app-header" data-testid="app-header">
      <div className="max-w-[1440px] mx-auto px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5" data-testid="header-logo">
          <div className="w-8 h-8 bg-inverse flex items-center justify-center">
            <Buildings size={18} color="#FFFFFF" weight="fill" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-display text-[15px] font-semibold tracking-tight">LIEN/TX</span>
            <span className="text-[9px] uppercase tracking-[0.2em] text-ink-tertiary mt-0.5">
              Property Intelligence
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              data-testid={`nav-${n.label.toLowerCase().replace(/\s+/g, "-")}`}
              className={
                "px-4 py-2 text-sm font-medium transition-colors " +
                (loc.pathname.startsWith(n.to)
                  ? "bg-inverse text-white"
                  : "text-ink hover:bg-muted-bg")
              }
            >
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 swiss-card">
                <UserIcon size={14} />
                <span className="text-sm font-medium">{user.name}</span>
              </div>
              <button
                onClick={() => {
                  logout();
                  nav("/");
                }}
                className="btn-ghost flex items-center gap-1.5"
                data-testid="header-logout-btn"
              >
                <SignOut size={16} />
                <span className="hidden sm:inline text-sm">Sign out</span>
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost text-sm" data-testid="header-login-btn">
                Sign in
              </Link>
              <Link to="/register" className="btn-primary text-sm" data-testid="header-register-btn">
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

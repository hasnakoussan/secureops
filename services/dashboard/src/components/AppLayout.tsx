import { type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[var(--color-bg)]">
      <aside className="w-full md:w-60 md:shrink-0 border-b md:border-b-0 md:border-r border-[var(--color-border)] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 md:py-6">
          <span className="font-mono font-semibold text-lg tracking-tight">
            Secure<span className="text-[var(--color-accent)]">Ops</span>
          </span>

          {user && (
            <button
              onClick={logout}
              className="md:hidden text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
            >
              Déconnexion
            </button>
          )}
        </div>

        <nav className="flex md:flex-col overflow-x-auto md:overflow-visible gap-1 px-3 pb-3 md:pb-0 md:flex-1">
          <NavLink to="/scans" label="Scans" active={location.pathname.startsWith("/scans")} />
          <NavLink to="/new-scan" label="Nouveau scan" active={location.pathname === "/new-scan"} />
          <NavLink to="/team" label="Équipe" active={location.pathname === "/team"} />
        </nav>

        {user && (
          <div className="hidden md:block px-5 py-4 border-t border-[var(--color-border)]">
            <p className="text-sm text-[var(--color-text)] truncate">{user.email}</p>
            <p className="text-xs text-[var(--color-text-muted)] truncate mb-3">
              {user.org_name} · {user.role}
            </p>
            <button
              onClick={logout}
              className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
            >
              Se déconnecter
            </button>
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

function NavLink({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Link
      to={to}
      className={`shrink-0 md:shrink block px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
        active
          ? "bg-[var(--color-surface)] text-[var(--color-text)]"
          : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]"
      }`}
    >
      {label}
    </Link>
  );
}

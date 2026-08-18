import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { ScoreGauge } from "../components/ScoreGauge";
import { Alert } from "../components/Alert";
import { Skeleton } from "../components/Skeleton";
import { listScans, type ScanSummary } from "../lib/scans";
import { ApiError } from "../lib/api";

export function ScanList() {
  const [scans, setScans] = useState<ScanSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    listScans()
      .then(setScans)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"));
  }, []);

  const filteredScans = useMemo(() => {
    if (!scans) return null;
    const q = query.trim().toLowerCase();
    if (!q) return scans;
    return scans.filter((scan) => scan.repo_url.toLowerCase().includes(q));
  }, [scans, query]);

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto px-8 py-10 animate-fade-in">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-xl font-semibold">Scans</h1>
            <p className="text-sm text-[var(--color-text-muted)] mt-1">
              Historique des analyses de sécurité de votre organisation
            </p>
          </div>
          <Link
            to="/new-scan"
            className="bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white text-sm font-medium rounded-md px-4 py-2 transition-colors"
          >
            Nouveau scan
          </Link>
        </div>

        {error && <Alert variant="error">{error}</Alert>}

        {scans !== null && scans.length > 0 && (
          <input
            type="text"
            placeholder="Filtrer par URL de repo..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full mb-6 font-mono text-sm"
          />
        )}

        {scans === null && !error && (
          <ul className="space-y-2" aria-label="Chargement des scans">
            {[1, 2, 3].map((i) => (
              <li key={i} className="flex items-center gap-4 border border-[var(--color-border)] rounded-lg px-4 py-3">
                <Skeleton className="w-10 h-10 rounded-full shrink-0" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {scans !== null && scans.length === 0 && (
          <div className="border border-dashed border-[var(--color-border)] rounded-lg py-16 text-center">
            <p className="text-[var(--color-text-muted)] text-sm mb-4">
              Aucun scan pour l'instant.
            </p>
            <Link to="/new-scan" className="text-[var(--color-accent)] text-sm hover:underline">
              Lancer votre premier scan
            </Link>
          </div>
        )}

        {filteredScans !== null && filteredScans.length === 0 && scans !== null && scans.length > 0 && (
          <p className="text-sm text-[var(--color-text-muted)] text-center py-10">
            Aucun scan ne correspond à « {query} ».
          </p>
        )}

        {filteredScans !== null && filteredScans.length > 0 && (
          <ul className="space-y-2">
            {filteredScans.map((scan) => (
              <li key={scan.id}>
                <Link
                  to={`/scans/${scan.id}`}
                  className="flex items-center gap-4 bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-lg px-4 py-3 transition-colors"
                >
                  {scan.score !== null && scan.classification !== null ? (
                    <ScoreGauge score={scan.score} classification={scan.classification} size={40} />
                  ) : (
                    <div className="w-10 h-10 rounded-full border-2 border-dashed border-[var(--color-border)]" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-mono truncate">{scan.repo_url}</p>
                    <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                      {scan.status === "completed" ? "Terminé" : scan.status}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppLayout>
  );
}

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { ScoreGauge } from "../components/ScoreGauge";
import { Alert } from "../components/Alert";
import { Skeleton } from "../components/Skeleton";
import { Spinner } from "../components/Spinner";
import { getScan, type ScanDetail as ScanDetailType, type Finding } from "../lib/scans";
import { ApiError } from "../lib/api";

const SOURCE_LABELS: Record<string, string> = {
  semgrep: "Semgrep — Analyse statique",
  gitleaks: "Gitleaks — Secrets",
  checkov: "Checkov — Infrastructure as Code",
  trivy: "Trivy — Dépendances (CVE)",
};

const SCANNER_NAMES: Record<string, string> = {
  semgrep: "Semgrep",
  gitleaks: "Gitleaks",
  checkov: "Checkov",
  trivy: "Trivy",
};

const POLL_INTERVAL_MS = 3000;

export function ScanDetail() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<ScanDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let intervalId: number | undefined;

    async function fetchScan() {
      try {
        const data = await getScan(Number(id));
        if (cancelled) return;
        setScan(data);
        if (data.status !== "pending" && intervalId !== undefined) {
          window.clearInterval(intervalId);
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError && err.status === 404
            ? "Ce scan n'existe pas ou n'appartient pas à votre organisation."
            : "Erreur de chargement",
        );
        if (intervalId !== undefined) window.clearInterval(intervalId);
      }
    }

    fetchScan();
    intervalId = window.setInterval(fetchScan, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId !== undefined) window.clearInterval(intervalId);
    };
  }, [id]);

  useEffect(() => {
    if (scan?.status !== "pending") return;
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [scan?.status]);

  if (error) {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto px-8 py-10">
          <Link to="/scans" className="text-sm text-[var(--color-accent)] hover:underline">
            ← Retour aux scans
          </Link>
          <div className="mt-4">
            <Alert variant="error">{error}</Alert>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!scan) {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto px-8 py-10" aria-label="Chargement du scan">
          <div className="flex items-start gap-6 mt-4 mb-10">
            <Skeleton className="w-28 h-28 rounded-full shrink-0" />
            <div className="flex-1 space-y-3 pt-1">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        </div>
      </AppLayout>
    );
  }

  if (scan.status === "pending") {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto px-8 py-10 animate-fade-in">
          <Link to="/scans" className="text-sm text-[var(--color-accent)] hover:underline">
            ← Retour aux scans
          </Link>

          <div className="mt-10 flex flex-col items-center text-center py-16">
            <Spinner className="h-8 w-8 text-[var(--color-accent)]" />
            <h1 className="text-lg font-medium mt-4">Scan en cours</h1>
            <p className="text-sm font-mono text-[var(--color-text-muted)] mt-1 break-all">
              {scan.repo_url}
            </p>
            <p className="text-xs text-[var(--color-text-muted)] mt-4">
              Temps écoulé : {elapsedSeconds}s — généralement 1 à 2 minutes selon la taille du
              repo. Cette page se met à jour automatiquement.
            </p>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (scan.status === "failed") {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto px-8 py-10 animate-fade-in">
          <Link to="/scans" className="text-sm text-[var(--color-accent)] hover:underline">
            ← Retour aux scans
          </Link>
          <h1 className="text-lg font-mono break-all mt-4 mb-4">{scan.repo_url}</h1>
          <Alert variant="error">
            {scan.error_message ?? "Ce scan a échoué pour une raison inconnue."}
          </Alert>
        </div>
      </AppLayout>
    );
  }

  const findingsBySource = scan.findings.reduce<Record<string, Finding[]>>((acc, finding) => {
    (acc[finding.source] ??= []).push(finding);
    return acc;
  }, {});

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto px-8 py-10 animate-fade-in">
        <Link to="/scans" className="text-sm text-[var(--color-accent)] hover:underline">
          ← Retour aux scans
        </Link>

        <div className="flex items-start gap-6 mt-4 mb-10">
          {scan.score !== null && scan.classification !== null && (
            <ScoreGauge score={scan.score} classification={scan.classification} size={112} />
          )}
          <div className="min-w-0 pt-1">
            <h1 className="text-lg font-mono break-all">{scan.repo_url}</h1>
            <div className="flex gap-4 mt-3 text-sm text-[var(--color-text-muted)]">
              <span>{scan.critical_count} critique{scan.critical_count !== 1 ? "s" : ""}</span>
              <span>{scan.high_count} élevé{scan.high_count !== 1 ? "s" : ""}</span>
              <span>{scan.medium_count} moyen{scan.medium_count !== 1 ? "s" : ""}</span>
              <span>{scan.secrets_count} secret{scan.secrets_count !== 1 ? "s" : ""}</span>
            </div>
          </div>
        </div>

        {scan.failed_scanners.length > 0 && (
          <div className="mb-6">
            <Alert variant="warning">
              {scan.failed_scanners.map((s) => SCANNER_NAMES[s] ?? s).join(", ")}
              {scan.failed_scanners.length === 1 ? " n'a" : " n'ont"} pas pu s'exécuter sur ce
              scan — le résultat ci-dessous est partiel.
            </Alert>
          </div>
        )}

        {scan.findings.length === 0 ? (
          <Alert variant="success">Aucun problème détecté par les scanners.</Alert>
        ) : (
          <div className="space-y-8">
            {Object.entries(findingsBySource).map(([source, findings]) => (
              <section key={source}>
                <h2 className="text-sm font-medium text-[var(--color-text-muted)] uppercase tracking-wide mb-3">
                  {SOURCE_LABELS[source] ?? source} ({findings.length})
                </h2>
                <ul className="space-y-2">
                  {findings.map((finding, i) => (
                    <li
                      key={i}
                      className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <code className="text-xs text-[var(--color-accent)] font-mono">
                          {finding.rule_id}
                        </code>
                        {finding.severity && (
                          <span className="text-xs font-mono text-[var(--color-text-muted)] shrink-0">
                            {finding.severity}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-mono text-[var(--color-text-muted)] mt-1.5">
                        {finding.file_path}
                        {finding.line > 0 && `:${finding.line}`}
                      </p>
                      {finding.message && (
                        <p className="text-sm mt-2 text-[var(--color-text)]">{finding.message}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}

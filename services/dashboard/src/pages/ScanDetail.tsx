import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { ScoreGauge } from "../components/ScoreGauge";
import { Alert } from "../components/Alert";
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

export function ScanDetail() {
  const { id } = useParams<{ id: string }>();
  const [scan, setScan] = useState<ScanDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getScan(Number(id))
      .then(setScan)
      .catch((err) =>
        setError(err instanceof ApiError && err.status === 404
          ? "Ce scan n'existe pas ou n'appartient pas à votre organisation."
          : "Erreur de chargement"),
      );
  }, [id]);

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
        <div className="max-w-4xl mx-auto px-8 py-10">
          <p className="text-sm text-[var(--color-text-muted)]">Chargement...</p>
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
      <div className="max-w-4xl mx-auto px-8 py-10">
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

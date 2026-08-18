import { useState, useEffect, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { Field } from "./Login";
import { Alert } from "../components/Alert";
import { createScan } from "../lib/scans";
import { ApiError } from "../lib/api";

const SCANNERS = ["Semgrep", "Gitleaks", "Checkov", "Trivy"];

// Validation légère côté client : on vérifie que l'URL ressemble à un
// repo Git avant d'envoyer la requête, pour éviter de faire attendre
// l'utilisateur 1-2 minutes juste pour découvrir une faute de frappe
// évidente. Le backend reste la source de vérité finale (cette
// validation n'essaie pas d'être exhaustive).
function looksLikeGitUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && parsed.pathname.length > 1;
  } catch {
    return false;
  }
}

export function NewScan() {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isScanning) return;
    const interval = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [isScanning]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!looksLikeGitUrl(repoUrl)) {
      setError("Cette URL ne semble pas valide. Format attendu : https://github.com/user/repo.git");
      return;
    }

    setIsScanning(true);
    setElapsedSeconds(0);
    try {
      const scan = await createScan(repoUrl);
      navigate(`/scans/${scan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Le scan a échoué");
      setIsScanning(false);
    }
  }

  return (
    <AppLayout>
      <div className="max-w-lg mx-auto px-8 py-10 animate-fade-in">
        <h1 className="text-xl font-semibold mb-1">Nouveau scan</h1>
        <p className="text-sm text-[var(--color-text-muted)] mb-8">
          Analyse un repo public avec Semgrep, Gitleaks, Checkov et Trivy.
        </p>

        <form
          onSubmit={handleSubmit}
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6 space-y-4"
        >
          {error && <Alert variant="error">{error}</Alert>}

          <Field label="URL du repo Git">
            <input
              type="url"
              required
              placeholder="https://github.com/utilisateur/repo.git"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              disabled={isScanning}
              className="w-full font-mono"
            />
          </Field>

          <button
            type="submit"
            disabled={isScanning}
            className="w-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-60 text-white font-medium text-sm rounded-md py-2 transition-colors flex items-center justify-center gap-2"
          >
            {isScanning && <Spinner />}
            {isScanning ? `Scan en cours... ${elapsedSeconds}s` : "Lancer le scan"}
          </button>

          {isScanning && (
            <div className="text-xs text-[var(--color-text-muted)] space-y-2 pt-2 border-t border-[var(--color-border)]">
              <p>
                Le clonage puis les 4 scanners tournent l'un après l'autre — comptez
                généralement 1 à 2 minutes selon la taille du repo :
              </p>
              <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono">
                {SCANNERS.map((name) => (
                  <li key={name}>· {name}</li>
                ))}
              </ul>
              <p>Cette page se mettra à jour automatiquement à la fin.</p>
            </div>
          )}
        </form>
      </div>
    </AppLayout>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

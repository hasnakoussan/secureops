import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
import { Field } from "./Login";
import { Alert } from "../components/Alert";
import { Spinner } from "../components/Spinner";
import { createScan } from "../lib/scans";
import { ApiError } from "../lib/api";

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
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!looksLikeGitUrl(repoUrl)) {
      setError("Cette URL ne semble pas valide. Format attendu : https://github.com/user/repo.git");
      return;
    }

    setIsSubmitting(true);
    try {
      const scan = await createScan(repoUrl);
      navigate(`/scans/${scan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de lancer le scan");
      setIsSubmitting(false);
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
              disabled={isSubmitting}
              className="w-full font-mono"
            />
          </Field>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-60 text-white font-medium text-sm rounded-md py-2 transition-colors flex items-center justify-center gap-2"
          >
            {isSubmitting && <Spinner />}
            {isSubmitting ? "Lancement..." : "Lancer le scan"}
          </button>
        </form>
      </div>
    </AppLayout>
  );
}

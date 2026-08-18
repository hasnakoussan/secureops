import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";
import { Alert } from "../components/Alert";
import { Field } from "./Login";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await register(orgName, email, password);
      navigate("/scans");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible de créer le compte");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="font-mono font-semibold text-2xl tracking-tight">
            Secure<span className="text-[var(--color-accent)]">Ops</span>
          </span>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6 space-y-4"
        >
          <h1 className="text-lg font-medium mb-1">Créer une organisation</h1>

          {error && <Alert variant="error">{error}</Alert>}

          <Field label="Nom de l'organisation">
            <input
              type="text"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full"
            />
          </Field>

          <Field label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full"
              autoComplete="email"
            />
          </Field>

          <Field label="Mot de passe (8 caractères min.)">
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full"
              autoComplete="new-password"
            />
          </Field>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-50 text-white font-medium text-sm rounded-md py-2 transition-colors"
          >
            {isSubmitting ? "Création..." : "Créer le compte"}
          </button>
        </form>

        <p className="text-center text-sm text-[var(--color-text-muted)] mt-4">
          Déjà un compte ?{" "}
          <Link to="/login" className="text-[var(--color-accent)] hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}

import { useEffect, useState, type FormEvent } from "react";
import { AppLayout } from "../components/AppLayout";
import { Alert } from "../components/Alert";
import { Field } from "./Login";
import { useAuth } from "../context/AuthContext";
import { listMembers, inviteMember, type Member, type InviteResult } from "../lib/members";
import { ApiError } from "../lib/api";

const ROLE_LABELS: Record<string, string> = {
  owner: "Propriétaire",
  admin: "Admin",
  member: "Membre",
  viewer: "Lecteur",
};

export function Team() {
  const { user } = useAuth();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canInvite = user?.role === "owner" || user?.role === "admin";

  function loadMembers() {
    listMembers()
      .then(setMembers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erreur de chargement"));
  }

  useEffect(loadMembers, []);

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto px-8 py-10 animate-fade-in">
        <h1 className="text-xl font-semibold mb-1">Équipe</h1>
        <p className="text-sm text-[var(--color-text-muted)] mb-8">
          Membres de {user?.org_name}
        </p>

        {error && <Alert variant="error">{error}</Alert>}

        {canInvite && <InviteForm onInvited={loadMembers} />}

        <MemberList members={members} />
      </div>
    </AppLayout>
  );
}

function MemberList({ members }: { members: Member[] | null }) {
  if (members === null) {
    return <p className="text-sm text-[var(--color-text-muted)]">Chargement...</p>;
  }

  return (
    <ul className="space-y-2 mt-6">
      {members.map((member) => (
        <li
          key={member.id}
          className="flex items-center justify-between bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3"
        >
          <span className="text-sm">{member.email}</span>
          <span className="text-xs font-mono uppercase text-[var(--color-text-muted)]">
            {ROLE_LABELS[member.role] ?? member.role}
          </span>
        </li>
      ))}
    </ul>
  );
}

function InviteForm({ onInvited }: { onInvited: () => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<InviteResult | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setIsSubmitting(true);
    try {
      const invited = await inviteMember(email, role);
      setResult(invited);
      setEmail("");
      onInvited();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Impossible d'inviter ce membre");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-6 mb-6">
      <h2 className="text-sm font-medium mb-4">Inviter un membre</h2>

      {error && <Alert variant="error">{error}</Alert>}

      {result && (
        <div className="mb-4">
          <Alert variant="success">
            {result.email} a été invité en tant que {ROLE_LABELS[result.role] ?? result.role}.
          </Alert>
          <div className="mt-2 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md px-3 py-2">
            <p className="text-xs text-[var(--color-text-muted)] mb-1">
              Mot de passe temporaire — pas encore d'envoi d'email automatique, transmettez-le
              manuellement :
            </p>
            <code className="text-sm font-mono text-[var(--color-accent)] select-all">
              {result.temporary_password}
            </code>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-3 items-end">
        <div className="flex-1">
          <Field label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full"
              disabled={isSubmitting}
            />
          </Field>
        </div>

        <label className="block">
          <span className="block text-xs font-medium text-[var(--color-text-muted)] mb-1.5">
            Rôle
          </span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={isSubmitting}
            className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md px-3 py-2 text-sm text-[var(--color-text)]"
          >
            <option value="admin">Admin</option>
            <option value="member">Membre</option>
            <option value="viewer">Lecteur</option>
          </select>
        </label>

        <button
          type="submit"
          disabled={isSubmitting}
          className="bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] disabled:opacity-60 text-white font-medium text-sm rounded-md px-4 py-2 transition-colors"
        >
          {isSubmitting ? "Envoi..." : "Inviter"}
        </button>
      </form>
    </div>
  );
}

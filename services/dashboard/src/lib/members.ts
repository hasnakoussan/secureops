// members.ts — fonctions d'appel de l'Auth Service liées à l'équipe.

import { authRequest } from "./api";

export interface Member {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface InviteResult {
  email: string;
  role: string;
  org_id: number;
  temporary_password: string;
}

export function listMembers() {
  return authRequest<Member[]>("/auth/users");
}

export function inviteMember(email: string, role: string) {
  return authRequest<InviteResult>("/auth/invite", {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

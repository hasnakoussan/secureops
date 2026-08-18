import { authRequest } from "./api";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  role: string;
  org_id: number;
  org_name: string;
}

export function register(orgName: string, email: string, password: string) {
  return authRequest<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ org_name: orgName, email, password }),
  });
}

export function login(email: string, password: string) {
  return authRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe() {
  return authRequest<CurrentUser>("/auth/me");
}

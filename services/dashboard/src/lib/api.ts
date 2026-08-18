const AUTH_BASE_URL = "http://localhost:8001";
const SCAN_BASE_URL = "http://localhost:8000";

const ACCESS_TOKEN_KEY = "secureops_access_token";
const REFRESH_TOKEN_KEY = "secureops_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  baseUrl: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${baseUrl}${path}`, { ...options, headers });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // pas de corps JSON
    }
    if (response.status === 401) {
      // Token expiré ou invalide : prévenir AuthContext pour
      // nettoyer la session et déconnecter proprement l'utilisateur.
      window.dispatchEvent(new CustomEvent("secureops:unauthorized"));
    }

    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function authRequest<T>(path: string, options?: RequestInit): Promise<T> {
  return request<T>(AUTH_BASE_URL, path, options);
}

export function scanRequest<T>(path: string, options?: RequestInit): Promise<T> {
  return request<T>(SCAN_BASE_URL, path, options);
}

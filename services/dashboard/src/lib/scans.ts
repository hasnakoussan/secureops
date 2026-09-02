// scans.ts — fonctions d'appel du Scan Service, typées.

import { scanRequest } from "./api";

export type Classification = "Safe" | "Warning" | "Critical";

export interface ScanSummary {
  id: number;
  repo_url: string;
  score: number | null;
  classification: Classification | null;
  status: string;
}

export interface Finding {
  source: string;
  rule_id: string;
  file_path: string;
  line: number;
  severity: string | null;
  message: string | null;
}

export interface ScanDetail extends ScanSummary {
  critical_count: number;
  high_count: number;
  medium_count: number;
  secrets_count: number;
  findings: Finding[];
  failed_scanners: string[];
  error_message: string | null;
}

export function listScans() {
  return scanRequest<ScanSummary[]>("/scans");
}

export function getScan(id: number) {
  return scanRequest<ScanDetail>(`/scans/${id}`);
}

export function createScan(repoUrl: string) {
  // Phase 4 : endpoint ASYNCHRONE côté backend — cette promesse se
  // résout quasi immédiatement (202 Accepted), avec un scan status
  // "pending" et aucun résultat encore. Le vrai traitement se fait en
  // arrière-plan par le Worker ; c'est ScanDetail qui sonde ensuite
  // GET /scans/{id} jusqu'à ce que le résultat soit prêt.
  return scanRequest<ScanDetail>("/scans", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

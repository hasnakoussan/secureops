"""
persistence.py — Phase 4 : sauvegarde des résultats de scan en base

Le flux réel de l'application passe par create_pending_scan() (appelé
par l'API) puis update_scan_with_results() ou mark_scan_failed() (appelés
par le Worker), pour permettre le traitement asynchrone via RabbitMQ.
"""

from datetime import datetime, timezone
import json

from models import Scan, Finding as DBFinding
from risk_engine import RiskAssessment
from semgrep_runner import ScanResult as SemgrepScanResult
from gitleaks_runner import SecretScanResult
from checkov_runner import IacScanResult
from trivy_runner import DependencyScanResult


def _compute_failed_scanners(semgrep_result, gitleaks_result, checkov_result, trivy_result) -> list[str]:
    """Tous les scanners sont toujours tentés — None signifie échec."""
    failed = []
    if semgrep_result is None:
        failed.append("semgrep")
    if gitleaks_result is None:
        failed.append("gitleaks")
    if checkov_result is None:
        failed.append("checkov")
    if trivy_result is None:
        failed.append("trivy")
    return failed


def _append_findings(scan: Scan, semgrep_result, gitleaks_result, checkov_result, trivy_result) -> None:
    """Construit les DBFinding à partir des résultats bruts et les rattache à `scan`."""
    if semgrep_result is not None and semgrep_result.success:
        for f in semgrep_result.findings:
            scan.findings.append(DBFinding(
                source="semgrep", rule_id=f.rule_id, file_path=f.file_path,
                line=f.line, severity=f.severity, message=f.message,
            ))

    if gitleaks_result is not None and gitleaks_result.success:
        for f in gitleaks_result.findings:
            scan.findings.append(DBFinding(
                source="gitleaks", rule_id=f.rule_id, file_path=f.file_path,
                line=f.line, severity=None, message=f.match,
            ))

    if checkov_result is not None and checkov_result.success:
        for f in checkov_result.findings:
            scan.findings.append(DBFinding(
                source="checkov", rule_id=f.check_id, file_path=f.file_path,
                line=f.line, severity=None, message=f"{f.resource}: {f.check_name}",
            ))

    if trivy_result is not None and trivy_result.success:
        for f in trivy_result.findings:
            fix_info = f"-> {f.fixed_version}" if f.fixed_version else "(pas de fix disponible)"
            scan.findings.append(DBFinding(
                source="trivy", rule_id=f.cve_id, file_path=f.file_path,
                line=0,
                severity=f.severity,
                message=f"{f.package_name} {f.installed_version} {fix_info}",
            ))


def create_pending_scan(session, org_id: int, repo_url: str) -> Scan:
    """
    Crée une ligne Scan avec status="pending" — c'est ce que l'API crée
    immédiatement à la réception de POST /scan, AVANT que le Worker
    n'ait fait le moindre travail.
    """
    scan = Scan(org_id=org_id, repo_url=repo_url, status="pending")
    session.add(scan)
    session.commit()
    return scan


def update_scan_with_results(
    session,
    scan_id: int,
    assessment: RiskAssessment,
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
) -> Scan:
    """Met à jour un scan existant (créé via create_pending_scan) avec ses résultats."""
    scan = session.query(Scan).filter(Scan.id == scan_id).first()
    if scan is None:
        raise ValueError(f"Scan {scan_id} introuvable — impossible de le mettre à jour")

    failed = _compute_failed_scanners(semgrep_result, gitleaks_result, checkov_result, trivy_result)

    scan.score = assessment.score
    scan.classification = assessment.classification
    scan.critical_count = assessment.summary.critical
    scan.high_count = assessment.summary.high
    scan.medium_count = assessment.summary.medium
    scan.secrets_count = assessment.summary.secrets_found
    scan.status = "completed"
    scan.failed_scanners = json.dumps(failed) if failed else None
    scan.finished_at = datetime.now(timezone.utc)

    _append_findings(scan, semgrep_result, gitleaks_result, checkov_result, trivy_result)

    session.commit()
    return scan


def mark_scan_failed(session, scan_id: int, error_message: str) -> Scan:
    """Marque un scan comme entièrement échoué (clone impossible, tous les scanners en échec)."""
    scan = session.query(Scan).filter(Scan.id == scan_id).first()
    if scan is None:
        raise ValueError(f"Scan {scan_id} introuvable — impossible de le marquer en échec")

    scan.status = "failed"
    scan.error_message = error_message
    scan.finished_at = datetime.now(timezone.utc)

    session.commit()
    return scan


def save_scan_result(
    session,
    org_id: int,
    repo_url: str,
    assessment: RiskAssessment,
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
) -> Scan:
    """
    Crée ET remplit un scan en une seule étape — gardé pour les scripts
    de test/exploration en ligne de commande. Le flux réel passe par
    create_pending_scan() puis update_scan_with_results() séparément.
    """
    failed = _compute_failed_scanners(semgrep_result, gitleaks_result, checkov_result, trivy_result)

    scan = Scan(
        org_id=org_id,
        repo_url=repo_url,
        score=assessment.score,
        classification=assessment.classification,
        critical_count=assessment.summary.critical,
        high_count=assessment.summary.high,
        medium_count=assessment.summary.medium,
        secrets_count=assessment.summary.secrets_found,
        status="completed",
        failed_scanners=json.dumps(failed) if failed else None,
        finished_at=datetime.now(timezone.utc),
    )

    _append_findings(scan, semgrep_result, gitleaks_result, checkov_result, trivy_result)

    session.add(scan)
    session.commit()

    return scan

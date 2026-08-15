"""
persistence.py — Phase 2 : sauvegarde des résultats de scan en base

Fait le pont entre les objets Python de notre pipeline (RiskAssessment,
Finding, SecretFinding, IacFinding, DependencyFinding) et les modèles
SQLAlchemy (Scan, Finding en DB).
"""

from datetime import datetime, timezone

from models import Scan, Finding as DBFinding
from risk_engine import RiskAssessment
from semgrep_runner import ScanResult as SemgrepScanResult
from gitleaks_runner import SecretScanResult
from checkov_runner import IacScanResult
from trivy_runner import DependencyScanResult


def save_scan_result(
    session,
    repo_url: str,
    assessment: RiskAssessment,
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
) -> Scan:
    """
    Sauvegarde un scan complet (résumé + findings détaillés des 4 scanners)
    en base.

    Notes sur le mapping des champs Checkov/Trivy vers la table findings
    (conçue à l'origine pour Semgrep/Gitleaks) :
        - rule_id : check_id (Checkov) ou cve_id (Trivy)
        - message : ressource concernée (Checkov) ou résumé
          package/version (Trivy)
        - severity : None pour Checkov (pas de sévérité native en OSS),
          la vraie sévérité Trivy sinon
        - line : 0 pour Trivy (vulnérabilité au niveau du package)
    """
    scan = Scan(
        repo_url=repo_url,
        score=assessment.score,
        classification=assessment.classification,
        critical_count=assessment.summary.critical,
        high_count=assessment.summary.high,
        medium_count=assessment.summary.medium,
        secrets_count=assessment.summary.secrets_found,
        status="completed",
        finished_at=datetime.now(timezone.utc),
    )

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

    session.add(scan)
    session.commit()

    return scan


if __name__ == "__main__":
    from models import get_engine, init_db, get_session
    from clone_manager import clone_repository, cleanup_repository
    from semgrep_runner import run_semgrep
    from gitleaks_runner import run_gitleaks
    from checkov_runner import run_checkov
    from trivy_runner import run_trivy
    from risk_engine import assess_risk

    engine = get_engine("sqlite:///test_secureops.db")
    init_db(engine)
    session = get_session(engine)

    repo_url = "https://github.com/pallets/flask.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if clone_result.success:
        semgrep_result = run_semgrep(clone_result.local_path)
        if not semgrep_result.success:
            semgrep_result = None

        gitleaks_result = run_gitleaks(clone_result.local_path)
        if not gitleaks_result.success:
            gitleaks_result = None

        checkov_result = run_checkov(clone_result.local_path)
        if not checkov_result.success:
            checkov_result = None

        trivy_result = run_trivy(clone_result.local_path)
        if not trivy_result.success:
            trivy_result = None

        assessment = assess_risk(semgrep_result, gitleaks_result, checkov_result, trivy_result)

        saved_scan = save_scan_result(
            session, repo_url, assessment,
            semgrep_result, gitleaks_result, checkov_result, trivy_result
        )
        print(f"✅ Scan sauvegardé en DB avec id={saved_scan.id}")
        print(f"   score={saved_scan.score}, findings={len(saved_scan.findings)}")

        from collections import Counter
        sources = Counter(f.source for f in saved_scan.findings)
        for source, count in sources.items():
            print(f"   - {source}: {count}")

        cleanup_repository(clone_result.local_path)

    session.close()

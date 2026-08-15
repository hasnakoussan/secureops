"""
risk_engine.py — Phase 2 : calcul du score de risque (4 scanners)

Agrège les résultats de Semgrep, Gitleaks, Checkov et Trivy et produit
un score exploitable (0-100) + une classification (Safe/Warning/Critical).

La normalisation des sévérités (spécifique à chaque scanner) est déléguée
à normalize.py — ce fichier se concentre uniquement sur le calcul du
score et la classification, une fois les findings déjà normalisés.

Voir blueprint section 3.4.
"""

from dataclasses import dataclass, field

from semgrep_runner import ScanResult as SemgrepScanResult
from gitleaks_runner import SecretScanResult
from checkov_runner import IacScanResult
from trivy_runner import DependencyScanResult
from normalize import normalize_findings as _normalize_findings


@dataclass
class FindingsSummary:
    """
    Comptage normalisé des findings, tous scanners confondus.

    Le détail du mapping par scanner vit désormais dans normalize.py.
    """
    critical: int = 0
    high: int = 0
    medium: int = 0
    secrets_found: int = 0


@dataclass
class RiskAssessment:
    """Résultat final : score + classification + détail des comptages."""
    score: int
    classification: str
    summary: FindingsSummary
    total_findings: int


def normalize_findings(
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
) -> FindingsSummary:
    """
    Convertit les résultats bruts des scanners en comptage normalisé.
    Délègue le mapping à normalize.normalize_findings().
    """
    counts = _normalize_findings(semgrep_result, gitleaks_result, checkov_result, trivy_result)
    return FindingsSummary(
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        secrets_found=counts["secrets_found"],
    )


def calculate_score(summary: FindingsSummary) -> int:
    """
    Calcule le score de risque (0-100).
    Formule (blueprint 3.4) : 100 - 20*critical - 10*high - 3*medium - 15*secrets
    """
    score = 100
    score -= summary.critical * 20
    score -= summary.high * 10
    score -= summary.medium * 3
    score -= summary.secrets_found * 15
    return max(score, 0)


def classify(score: int) -> str:
    """Traduit un score numérique en statut lisible."""
    if score >= 80:
        return "Safe"
    if score >= 50:
        return "Warning"
    return "Critical"


def assess_risk(
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
) -> RiskAssessment:
    """Point d'entrée principal : résultats bruts -> évaluation de risque."""
    summary = normalize_findings(semgrep_result, gitleaks_result, checkov_result, trivy_result)
    score = calculate_score(summary)
    classification = classify(score)
    total = summary.critical + summary.high + summary.medium + summary.secrets_found

    return RiskAssessment(
        score=score,
        classification=classification,
        summary=summary,
        total_findings=total,
    )


if __name__ == "__main__":
    from clone_manager import clone_repository, cleanup_repository
    from semgrep_runner import run_semgrep
    from gitleaks_runner import run_gitleaks
    from checkov_runner import run_checkov
    from trivy_runner import run_trivy

    repo_url = "https://github.com/pallets/flask.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
    else:
        print(f"✅ Cloné dans {clone_result.local_path}")

        print("Lancement de Semgrep...")
        semgrep_result = run_semgrep(clone_result.local_path)
        print(f"  {'✅' if semgrep_result.success else '❌'} "
              + (f"{len(semgrep_result.findings)} findings" if semgrep_result.success
                 else semgrep_result.error_message))

        print("Lancement de Gitleaks...")
        gitleaks_result = run_gitleaks(clone_result.local_path)
        print(f"  {'✅' if gitleaks_result.success else '❌'} "
              + (f"{len(gitleaks_result.findings)} secrets" if gitleaks_result.success
                 else gitleaks_result.error_message))

        print("Lancement de Checkov...")
        checkov_result = run_checkov(clone_result.local_path)
        print(f"  {'✅' if checkov_result.success else '❌'} "
              + (f"{len(checkov_result.findings)} findings IaC" if checkov_result.success
                 else checkov_result.error_message))

        print("Lancement de Trivy...")
        trivy_result = run_trivy(clone_result.local_path)
        print(f"  {'✅' if trivy_result.success else '❌'} "
              + (f"{len(trivy_result.findings)} CVE" if trivy_result.success
                 else trivy_result.error_message))

        print("\nCalcul du score...")
        assessment = assess_risk(semgrep_result, gitleaks_result, checkov_result, trivy_result)

        print(f"\n{'='*50}")
        print(f"SCORE : {assessment.score}/100 — {assessment.classification}")
        print(f"{'='*50}")
        print(f"  Critiques    : {assessment.summary.critical}")
        print(f"  Élevés       : {assessment.summary.high}")
        print(f"  Moyens       : {assessment.summary.medium}")
        print(f"  Secrets      : {assessment.summary.secrets_found}")
        print(f"  Total        : {assessment.total_findings}")

        cleanup_repository(clone_result.local_path)
        print("\n🧹 Nettoyage effectué")

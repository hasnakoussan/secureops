"""
normalize.py — Phase 2 : normalisation des findings par scanner

Chaque scanner a son propre vocabulaire de sévérité. Plutôt qu'une seule
grosse fonction avec un bloc if/elif par scanner (difficile à tester et
à faire évoluer sans rien oublier), on isole une fonction de mapping par
scanner : chacune a la responsabilité unique de traduire la sévérité
native de SON scanner vers le vocabulaire commun de SecureOps
("critical", "high", "medium", ou None si ignoré).

Avantages concrets de ce découpage :
    - Testable isolément : assert _map_semgrep_severity("MEDIUM") == "medium"
      sans avoir à construire tout un ScanResult.
    - Ajouter un 5e scanner = ajouter une fonction, pas complexifier
      normalize_findings().
    - Le bug qu'on a eu (le cas Semgrep "MEDIUM" silencieusement ignoré
      au premier passage) aurait été détecté immédiatement par un test
      unitaire ciblé, plutôt que découvert en observant un vrai scan.
"""

from semgrep_runner import ScanResult as SemgrepScanResult
from gitleaks_runner import SecretScanResult
from checkov_runner import IacScanResult
from trivy_runner import DependencyScanResult


def _map_semgrep_severity(severity: str) -> str | None:
    """
    Traduit une sévérité Semgrep vers le vocabulaire SecureOps.

    La plupart des règles Semgrep utilisent ERROR/WARNING/INFO, mais
    certaines catégories (règles supply-chain comme "package_managers.uv.*")
    utilisent un vocabulaire type CVSS (CRITICAL/HIGH/MEDIUM/LOW).
    """
    severity = severity.upper()
    if severity in ("ERROR", "CRITICAL"):
        return "critical"
    if severity in ("WARNING", "HIGH"):
        return "high"
    if severity == "MEDIUM":
        return "medium"
    return None  # INFO, LOW : volontairement ignorés


def _map_trivy_severity(severity: str) -> str | None:
    """Traduit une sévérité Trivy (CVE) vers le vocabulaire SecureOps."""
    severity = severity.upper()
    if severity == "CRITICAL":
        return "critical"
    if severity == "HIGH":
        return "high"
    if severity == "MEDIUM":
        return "medium"
    return None  # LOW, UNKNOWN : volontairement ignorés


def _map_checkov_severity() -> str:
    """
    Checkov (version OSS) n'a pas de sévérité graduée par règle — chaque
    check en échec est donc traité de façon uniforme comme "medium".
    """
    return "medium"


def _map_gitleaks_severity() -> str:
    """
    Gitleaks n'a pas de notion de sévérité : un secret trouvé est toujours
    grave par nature. Catégorie dédiée "secrets_found".
    """
    return "secrets_found"


def normalize_findings(
    semgrep_result: SemgrepScanResult | None,
    gitleaks_result: SecretScanResult | None,
    checkov_result: IacScanResult | None = None,
    trivy_result: DependencyScanResult | None = None,
):
    """
    Convertit les résultats bruts des 4 scanners en comptage normalisé.

    Retourne un dict simple {critical, high, medium, secrets_found} pour
    éviter une dépendance circulaire avec risk_engine.py.
    """
    counts = {"critical": 0, "high": 0, "medium": 0, "secrets_found": 0}

    if semgrep_result is not None and semgrep_result.success:
        for finding in semgrep_result.findings:
            category = _map_semgrep_severity(finding.severity)
            if category is not None:
                counts[category] += 1

    if gitleaks_result is not None and gitleaks_result.success:
        for _ in gitleaks_result.findings:
            counts[_map_gitleaks_severity()] += 1

    if checkov_result is not None and checkov_result.success:
        for _ in checkov_result.findings:
            counts[_map_checkov_severity()] += 1

    if trivy_result is not None and trivy_result.success:
        for finding in trivy_result.findings:
            category = _map_trivy_severity(finding.severity)
            if category is not None:
                counts[category] += 1

    return counts


if __name__ == "__main__":
    assert _map_semgrep_severity("ERROR") == "critical"
    assert _map_semgrep_severity("CRITICAL") == "critical"
    assert _map_semgrep_severity("WARNING") == "high"
    assert _map_semgrep_severity("HIGH") == "high"
    assert _map_semgrep_severity("MEDIUM") == "medium"
    assert _map_semgrep_severity("INFO") is None
    assert _map_semgrep_severity("LOW") is None
    print("✅ _map_semgrep_severity : tous les cas passent")

    assert _map_trivy_severity("CRITICAL") == "critical"
    assert _map_trivy_severity("HIGH") == "high"
    assert _map_trivy_severity("MEDIUM") == "medium"
    assert _map_trivy_severity("LOW") is None
    assert _map_trivy_severity("UNKNOWN") is None
    print("✅ _map_trivy_severity : tous les cas passent")

    assert _map_checkov_severity() == "medium"
    print("✅ _map_checkov_severity : ok")

    assert _map_gitleaks_severity() == "secrets_found"
    print("✅ _map_gitleaks_severity : ok")

    print("\n✅ Tous les tests de mapping passent.")

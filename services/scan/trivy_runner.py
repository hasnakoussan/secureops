"""
trivy_runner.py — Phase 2 : intégration Trivy (mode filesystem)

Lance Trivy sur un dossier de code (déjà cloné via clone_manager) pour
détecter des CVE connues dans les dépendances déclarées (requirements.txt,
package.json, go.mod, etc.).

Voir blueprint section 3.3, sous-composant "trivy_runner".

IMPORTANT — mode fs vs mode image :
    Trivy peut scanner soit le système de fichiers (dépendances déclarées
    dans des fichiers manifestes), soit une image Docker construite. On
    utilise ici le mode `fs`, cohérent avec le reste du pipeline actuel
    qui scanne un repo cloné, pas encore d'image Docker (ça viendra en
    Phase 3-4 avec la dockerisation complète du projet).
"""

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field


_DEFAULT_TRIVY_BIN = str(
    Path(__file__).resolve().parent.parent.parent / "bin" / "trivy"
)


@dataclass
class DependencyFinding:
    """Une vulnérabilité connue (CVE) détectée dans une dépendance."""
    cve_id: str
    package_name: str
    installed_version: str
    fixed_version: str | None
    severity: str            # CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
    file_path: str


@dataclass
class DependencyScanResult:
    """Résultat complet d'un scan Trivy."""
    success: bool
    findings: list[DependencyFinding] = field(default_factory=list)
    error_message: str | None = None


def run_trivy(target_path: str, trivy_bin: str = _DEFAULT_TRIVY_BIN, timeout: int = 180) -> DependencyScanResult:
    """
    Lance Trivy (mode fs) sur le dossier cible et parse les résultats.

    Notes:
        - Un repo sans fichier de dépendances reconnu est un cas NORMAL :
          Trivy retournera simplement 0 finding, pas une erreur.
        - --scanners vuln : on restreint Trivy aux CVE, pas aux secrets ou
          mauvaises configs (déjà couverts par Gitleaks et Checkov).
    """
    try:
        result = subprocess.run(
            [
                trivy_bin, "fs",
                "--scanners", "vuln",
                "--format", "json",
                "--quiet",
                target_path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return DependencyScanResult(
            success=False,
            error_message=f"Trivy a dépassé le timeout de {timeout}s",
        )
    except FileNotFoundError:
        return DependencyScanResult(
            success=False,
            error_message="Trivy n'est pas installé ou introuvable dans le PATH",
        )

    if not result.stdout.strip():
        return DependencyScanResult(
            success=False,
            error_message=f"Trivy n'a rien retourné. stderr: {result.stderr[:500]}",
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return DependencyScanResult(
            success=False,
            error_message=f"Impossible de parser la sortie JSON de Trivy. stderr: {result.stderr[:300]}",
        )

    findings = []
    for target_result in data.get("Results", []):
        file_path = target_result.get("Target", "unknown")
        for vuln in target_result.get("Vulnerabilities", []) or []:
            findings.append(
                DependencyFinding(
                    cve_id=vuln.get("VulnerabilityID", "unknown"),
                    package_name=vuln.get("PkgName", "unknown"),
                    installed_version=vuln.get("InstalledVersion", "unknown"),
                    fixed_version=vuln.get("FixedVersion") or None,
                    severity=vuln.get("Severity", "UNKNOWN"),
                    file_path=file_path,
                )
            )

    return DependencyScanResult(success=True, findings=findings)


if __name__ == "__main__":
    from clone_manager import clone_repository, cleanup_repository

    repo_url = "https://github.com/pallets/flask.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
    else:
        print(f"✅ Cloné dans {clone_result.local_path}")
        print("Lancement de Trivy (le premier lancement peut être long, "
              "le temps de télécharger la base de CVE)...")

        scan_result = run_trivy(clone_result.local_path)

        if scan_result.success:
            print(f"✅ Scan terminé : {len(scan_result.findings)} vulnérabilité(s)")
            for f in scan_result.findings[:5]:
                print(f"   [{f.severity}] {f.cve_id} — {f.package_name} "
                      f"{f.installed_version} (fix: {f.fixed_version or 'aucun'})")
        else:
            print(f"❌ Échec du scan : {scan_result.error_message}")

        cleanup_repository(clone_result.local_path)
        print("🧹 Nettoyage effectué")

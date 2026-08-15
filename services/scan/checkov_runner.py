"""
checkov_runner.py — Phase 2 : intégration Checkov

Lance Checkov sur un dossier de code (déjà cloné via clone_manager) pour
détecter des mauvaises configurations dans les fichiers Terraform.

Voir blueprint section 3.3, sous-composant "checkov_runner".
"""

import subprocess
import json
from dataclasses import dataclass, field


@dataclass
class IacFinding:
    """Une mauvaise configuration IaC détectée par Checkov."""
    check_id: str        # ex: "CKV_AWS_24"
    check_name: str       # description lisible de la règle
    file_path: str
    line: int
    resource: str          # ex: "aws_security_group.allow_all"


@dataclass
class IacScanResult:
    """Résultat complet d'un scan Checkov."""
    success: bool
    findings: list[IacFinding] = field(default_factory=list)
    error_message: str | None = None


def run_checkov(target_path: str, timeout: int = 120) -> IacScanResult:
    """
    Lance Checkov sur le dossier cible et parse les résultats.

    Notes:
        - --framework terraform : on restreint volontairement Checkov au
          framework Terraform. Par défaut, Checkov scanne aussi les secrets
          (check_type "secrets") — un chevauchement direct avec Gitleaks.
          Pour éviter de compter deux fois le même problème dans le score,
          chaque scanner reste responsable d'un seul domaine : Checkov =
          IaC, Gitleaks = secrets.
        - Un repo sans fichier Terraform est un cas NORMAL, pas une erreur :
          Checkov retournera simplement 0 finding.
    """
    try:
        result = subprocess.run(
            [
                "checkov",
                "-d", target_path,
                "--framework", "terraform",
                "--output", "json",
                "--quiet",
                "--compact",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return IacScanResult(
            success=False,
            error_message=f"Checkov a dépassé le timeout de {timeout}s",
        )
    except FileNotFoundError:
        return IacScanResult(
            success=False,
            error_message="Checkov n'est pas installé ou introuvable dans le PATH",
        )

    if not result.stdout.strip():
        return IacScanResult(
            success=False,
            error_message=f"Checkov n'a rien retourné. stderr: {result.stderr[:500]}",
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return IacScanResult(
            success=False,
            error_message="Impossible de parser la sortie JSON de Checkov",
        )

    failed_checks = data.get("results", {}).get("failed_checks", [])

    findings = []
    for check in failed_checks:
        line_range = check.get("file_line_range", [0, 0])
        findings.append(
            IacFinding(
                check_id=check.get("check_id", "unknown"),
                check_name=check.get("check_name", ""),
                file_path=check.get("file_path", "unknown"),
                line=line_range[0] if line_range else 0,
                resource=check.get("resource", "unknown"),
            )
        )

    return IacScanResult(success=True, findings=findings)


if __name__ == "__main__":
    from clone_manager import clone_repository, cleanup_repository

    repo_url = "https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
    else:
        print(f"✅ Cloné dans {clone_result.local_path}")
        print("Lancement de Checkov (peut prendre 30-60s)...")

        scan_result = run_checkov(clone_result.local_path)

        if scan_result.success:
            print(f"✅ Scan terminé : {len(scan_result.findings)} finding(s)")
            for f in scan_result.findings[:5]:
                print(f"   [{f.check_id}] {f.file_path}:{f.line} — {f.resource}")
        else:
            print(f"❌ Échec du scan : {scan_result.error_message}")

        cleanup_repository(clone_result.local_path)
        print("🧹 Nettoyage effectué")

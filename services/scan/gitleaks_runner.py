"""
gitleaks_runner.py — Phase 1 : intégration Gitleaks

Lance Gitleaks sur un dossier de code (déjà cloné via clone_manager) pour
détecter des secrets hardcodés (clés API, mots de passe, tokens...).

Voir blueprint section 3.3, sous-composant "gitleaks_runner".
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, field


# Chemin par défaut du binaire Gitleaks, calculé par rapport à l'emplacement
# de CE fichier (pas par rapport au dossier depuis lequel on lance le script).
# Ça évite le bug classique où "../../bin/gitleaks" ne marche que si on lance
# le script depuis un dossier précis.
_DEFAULT_GITLEAKS_BIN = str(
    Path(__file__).resolve().parent.parent.parent / "bin" / "gitleaks"
)


@dataclass
class SecretFinding:
    """Un secret détecté par Gitleaks."""
    rule_id: str       # ex: "generic-api-key", "aws-access-token"
    file_path: str
    line: int
    match: str          # extrait du secret trouvé (déjà partiellement masqué par Gitleaks)
    commit: str | None = None


@dataclass
class SecretScanResult:
    """Résultat complet d'un scan Gitleaks."""
    success: bool
    findings: list[SecretFinding] = field(default_factory=list)
    error_message: str | None = None


def run_gitleaks(target_path: str, gitleaks_bin: str = _DEFAULT_GITLEAKS_BIN, timeout: int = 60) -> SecretScanResult:
    """
    Lance Gitleaks sur le dossier cible et parse les résultats.

    Notes:
        - On utilise `gitleaks detect` en mode "no-git" (--no-git) car on
          scanne un shallow clone : l'historique Git est absent/incomplet.
        - Gitleaks écrit son rapport dans un fichier (--report-path).
    """
    if not os.path.isfile(gitleaks_bin):
        return SecretScanResult(
            success=False,
            error_message=f"Binaire Gitleaks introuvable à {gitleaks_bin}",
        )

    report_fd, report_path = tempfile.mkstemp(suffix=".json", prefix="gitleaks_report_")
    os.close(report_fd)

    try:
        result = subprocess.run(
            [
                gitleaks_bin, "detect",
                "--source", target_path,
                "--no-git",
                "--report-format", "json",
                "--report-path", report_path,
                "--exit-code", "0",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        os.remove(report_path) if os.path.exists(report_path) else None
        return SecretScanResult(
            success=False,
            error_message=f"Gitleaks a dépassé le timeout de {timeout}s",
        )

    if result.returncode != 0:
        os.remove(report_path) if os.path.exists(report_path) else None
        return SecretScanResult(
            success=False,
            error_message=f"Gitleaks a échoué (code {result.returncode}): {result.stderr[:500]}",
        )

    try:
        with open(report_path, "r") as f:
            content = f.read().strip()
            data = json.loads(content) if content else []
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return SecretScanResult(
            success=False,
            error_message=f"Impossible de lire le rapport Gitleaks: {e}",
        )
    finally:
        if os.path.exists(report_path):
            os.remove(report_path)

    findings = []
    for item in data:
        findings.append(
            SecretFinding(
                rule_id=item.get("RuleID", "unknown"),
                file_path=item.get("File", "unknown"),
                line=item.get("StartLine", 0),
                match=item.get("Match", ""),
                commit=item.get("Commit") or None,
            )
        )

    return SecretScanResult(success=True, findings=findings)


if __name__ == "__main__":
    from clone_manager import clone_repository, cleanup_repository

    repo_url = "https://github.com/pallets/flask.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
    else:
        print(f"✅ Cloné dans {clone_result.local_path}")
        print("Lancement de Gitleaks...")

        scan_result = run_gitleaks(clone_result.local_path)

        if scan_result.success:
            print(f"✅ Scan terminé : {len(scan_result.findings)} secret(s) trouvé(s)")
            for f in scan_result.findings[:5]:
                print(f"   [{f.rule_id}] {f.file_path}:{f.line}")
        else:
            print(f"❌ Échec du scan : {scan_result.error_message}")

        cleanup_repository(clone_result.local_path)
        print("🧹 Nettoyage effectué")

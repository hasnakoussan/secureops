"""
semgrep_runner.py — Phase 1 : intégration Semgrep

Lance Semgrep sur un dossier de code (déjà cloné via clone_manager) et
retourne les findings sous une forme structurée et exploitable.

Voir blueprint section 3.3, sous-composant "semgrep_runner".
"""

import subprocess
import json
from dataclasses import dataclass, field


@dataclass
class Finding:
    """Une vulnérabilité/problème détecté par Semgrep."""
    rule_id: str
    file_path: str
    line: int
    severity: str  # ERROR, WARNING, INFO (niveaux natifs de Semgrep)
    message: str


@dataclass
class ScanResult:
    """Résultat complet d'un scan Semgrep."""
    success: bool
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_message: str | None = None


def run_semgrep(target_path: str, timeout: int = 120) -> ScanResult:
    """
    Lance Semgrep sur le dossier cible et parse les résultats.

    Args:
        target_path: chemin local du code à scanner (ex: repo cloné)
        timeout: délai max en secondes avant d'abandonner le scan.

    Returns:
        ScanResult avec la liste des findings, ou un message d'erreur.

    Notes:
        - --config=auto : Semgrep détecte le(s) langage(s) présents et
          applique un ruleset générique adapté.
        - --json : sortie structurée, plus facile à parser qu'un rapport texte.
    """
    try:
        result = subprocess.run(
            ["semgrep", "--config=auto", "--json", "--quiet", target_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ScanResult(
            success=False,
            error_message=f"Semgrep a dépassé le timeout de {timeout}s",
        )
    except FileNotFoundError:
        return ScanResult(
            success=False,
            error_message="Semgrep n'est pas installé ou introuvable dans le PATH",
        )

    if not result.stdout.strip():
        return ScanResult(
            success=False,
            error_message=f"Semgrep n'a rien retourné. stderr: {result.stderr[:500]}",
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ScanResult(
            success=False,
            error_message="Impossible de parser la sortie JSON de Semgrep",
        )

    # Vérification importante : si le téléchargement du ruleset a échoué
    # totalement (ex: problème réseau), Semgrep retourne un JSON "valide"
    # mais n'a scanné AUCUN fichier — on veut détecter ce cas précis.
    #
    # ATTENTION : Semgrep signale aussi des erreurs "normales" et fréquentes,
    # comme des fichiers individuels illisibles (ex: templates Jinja2 avec
    # syntaxe {% %} que le parser HTML/JS ne comprend pas). Ces erreurs-là
    # NE DOIVENT PAS faire échouer tout le scan : Semgrep saute juste ces
    # fichiers et continue sur le reste. On distingue donc :
    #   - échec total : rien n'a été scanné (paths.scanned vide)
    #   - succès partiel : des fichiers ont été scannés, d'autres ignorés
    scanned_paths = data.get("paths", {}).get("scanned", [])
    errors = data.get("errors", [])

    if not scanned_paths and errors:
        error_messages = "; ".join(e.get("message", str(e)) for e in errors[:3])
        return ScanResult(
            success=False,
            error_message=f"Aucun fichier scanné (échec de configuration probable): {error_messages}",
        )

    findings = []
    for r in data.get("results", []):
        findings.append(
            Finding(
                rule_id=r.get("check_id", "unknown"),
                file_path=r.get("path", "unknown"),
                line=r.get("start", {}).get("line", 0),
                severity=r.get("extra", {}).get("severity", "INFO"),
                message=r.get("extra", {}).get("message", ""),
            )
        )

    # On garde une trace des erreurs partielles (fichiers ignorés) sans
    # faire échouer le scan — utile pour le rapport final ("scan réussi,
    # mais 5 fichiers n'ont pas pu être analysés").
    warnings = [e.get("message", str(e)) for e in errors] if scanned_paths else []

    return ScanResult(success=True, findings=findings, warnings=warnings)


if __name__ == "__main__":
    from clone_manager import clone_repository, cleanup_repository

    repo_url = "https://github.com/pallets/flask.git"
    print(f"Clonage de {repo_url}...")
    clone_result = clone_repository(repo_url)

    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
    else:
        print(f"✅ Cloné dans {clone_result.local_path}")
        print("Lancement de Semgrep (peut prendre 30-60s)...")

        scan_result = run_semgrep(clone_result.local_path)

        if scan_result.success:
            print(f"✅ Scan terminé : {len(scan_result.findings)} findings")
            for f in scan_result.findings[:5]:
                print(f"   [{f.severity}] {f.file_path}:{f.line} — {f.rule_id}")
            if scan_result.warnings:
                print(f"⚠️  {len(scan_result.warnings)} fichier(s) ignoré(s) (erreurs de parsing)")
        else:
            print(f"❌ Échec du scan : {scan_result.error_message}")

        cleanup_repository(clone_result.local_path)
        print("🧹 Nettoyage effectué")

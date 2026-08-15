"""
main.py — Phase 1 : point d'entrée du MVP local

Orchestre le pipeline complet : clone -> Semgrep + Gitleaks -> score.

Usage:
    python3 main.py <repo_url>

Exemple:
    python3 main.py https://github.com/pallets/flask.git

C'est la version "script CLI" du futur Scan Service. Le découpage en
microservices (Phase 4 du blueprint) réutilisera exactement cette même
logique métier, juste exposée via une API et un message queue au lieu
d'un simple argument en ligne de commande.
"""

import sys

from clone_manager import clone_repository, cleanup_repository
from semgrep_runner import run_semgrep
from gitleaks_runner import run_gitleaks
from risk_engine import assess_risk


def scan_repository(repo_url: str) -> None:
    """
    Pipeline complet pour un repo donné : clone, scanne avec les 2 outils,
    calcule le score, affiche un rapport lisible, nettoie.
    """
    print(f"🔍 SecureOps — Scan de {repo_url}\n")

    print("📥 Clonage du repo...")
    clone_result = clone_repository(repo_url)
    if not clone_result.success:
        print(f"❌ Échec du clone : {clone_result.error_message}")
        sys.exit(1)
    print(f"✅ Cloné dans {clone_result.local_path}\n")

    try:
        print("🔎 Analyse statique (Semgrep)...")
        semgrep_result = run_semgrep(clone_result.local_path)
        if semgrep_result.success:
            print(f"✅ {len(semgrep_result.findings)} finding(s)")
            if semgrep_result.warnings:
                print(f"⚠️  {len(semgrep_result.warnings)} fichier(s) ignoré(s)")
        else:
            print(f"❌ {semgrep_result.error_message}")
            semgrep_result = None
        print()

        print("🔑 Détection de secrets (Gitleaks)...")
        gitleaks_result = run_gitleaks(clone_result.local_path)
        if gitleaks_result.success:
            print(f"✅ {len(gitleaks_result.findings)} secret(s)")
        else:
            print(f"❌ {gitleaks_result.error_message}")
            gitleaks_result = None
        print()

        print("📊 Calcul du score de risque...")
        assessment = assess_risk(semgrep_result, gitleaks_result)

        print(f"\n{'='*50}")
        print(f"  SCORE : {assessment.score}/100  —  {assessment.classification}")
        print(f"{'='*50}")
        print(f"  Findings critiques : {assessment.summary.critical}")
        print(f"  Findings élevés     : {assessment.summary.high}")
        print(f"  Findings moyens     : {assessment.summary.medium}")
        print(f"  Secrets exposés     : {assessment.summary.secrets_found}")
        print(f"  Total               : {assessment.total_findings}")
        print(f"{'='*50}\n")

    finally:
        cleanup_repository(clone_result.local_path)
        print("🧹 Nettoyage effectué")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <repo_url>")
        print("Exemple: python3 main.py https://github.com/pallets/flask.git")
        sys.exit(1)

    scan_repository(sys.argv[1])

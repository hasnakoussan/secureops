"""
clone_manager.py — Phase 1 : clonage de repos GitHub

Ce module fournit une fonction pour cloner un repo public dans un dossier
temporaire isolé, avec shallow clone (--depth=1) et gestion d'erreurs.

C'est la première brique du futur Scan Service (voir blueprint section 3.3,
sous-composant "clone_manager").
"""

import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass

from git import Repo
from git.exc import GitCommandError


@dataclass
class CloneResult:
    """Résultat d'une opération de clonage."""
    success: bool
    local_path: str | None = None
    error_message: str | None = None


def clone_repository(repo_url: str, branch: str | None = None) -> CloneResult:
    """
    Clone un repo Git public dans un dossier temporaire unique.

    Args:
        repo_url: URL du repo (ex: "https://github.com/user/repo.git")
        branch: branche à cloner. Si None (défaut), clone la branche par
            défaut du repo — on ne peut PAS supposer que c'est "main":
            beaucoup de repos utilisent encore "master", ou un autre nom.
            Imposer "main" en dur casse le clone sur ces repos.

    Returns:
        CloneResult avec le chemin local si succès, ou un message d'erreur.

    Notes:
        - Shallow clone (depth=1) : on ne récupère que le dernier commit,
          pas tout l'historique. Suffisant pour scanner l'état actuel du code,
          et beaucoup plus rapide/léger que git clone --mirror.
        - Le dossier est créé dans /tmp (via tempfile), donc automatiquement
          isolé d'un scan à l'autre.
        - Cette fonction NE nettoie PAS le dossier après elle-même — c'est
          intentionnel : le Scan Service doit pouvoir lire les fichiers
          après le clone. Le nettoyage est la responsabilité de l'appelant
          (voir cleanup_repository ci-dessous).
    """
    temp_dir = tempfile.mkdtemp(prefix="secureops_scan_")

    try:
        clone_kwargs = {
            "url": repo_url,
            "to_path": temp_dir,
            "depth": 1,  # shallow clone
            "single_branch": True,
        }
        if branch is not None:
            clone_kwargs["branch"] = branch
        # Si branch est None, on n'ajoute pas l'option --branch :
        # git clone utilise alors automatiquement la branche par défaut
        # du repo distant (HEAD), quelle qu'elle soit.

        Repo.clone_from(**clone_kwargs)
        return CloneResult(success=True, local_path=temp_dir)

    except GitCommandError as e:
        # Le clone a échoué (repo inexistant, branche introuvable, réseau...)
        # On nettoie le dossier temporaire vide avant de remonter l'erreur.
        shutil.rmtree(temp_dir, ignore_errors=True)
        return CloneResult(success=False, error_message=str(e))

    except Exception as e:
        # Filet de sécurité pour toute autre erreur inattendue
        shutil.rmtree(temp_dir, ignore_errors=True)
        return CloneResult(success=False, error_message=f"Erreur inattendue: {e}")


def cleanup_repository(local_path: str) -> None:
    """
    Supprime le dossier temporaire d'un repo cloné.

    À appeler une fois le scan terminé (succès ou échec), pour ne pas
    accumuler des repos clonés dans /tmp.
    """
    path = Path(local_path)
    if path.exists() and path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    # Test manuel rapide : clone un petit repo public connu
    result = clone_repository("https://github.com/octocat/Hello-World.git")

    if result.success:
        print(f"✅ Clone réussi : {result.local_path}")
        files = list(Path(result.local_path).iterdir())
        print(f"   Fichiers présents : {[f.name for f in files]}")
        cleanup_repository(result.local_path)
        print("🧹 Nettoyage effectué")
    else:
        print(f"❌ Échec du clone : {result.error_message}")

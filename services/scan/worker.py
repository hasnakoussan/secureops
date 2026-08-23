"""
worker.py — Phase 4 : Worker asynchrone qui traite les scans

Processus séparé de l'API (à lancer dans un terminal à part). Écoute la
queue RabbitMQ "scan_requests", et pour chaque message : clone le repo,
lance les 4 scanners, calcule le score, met à jour la ligne Scan
correspondante en base.

Lancer avec : python3 worker.py
"""

import os
import json
import time
from dotenv import load_dotenv

load_dotenv("../../.env")

import pika

from models import get_engine, init_db, get_session, Scan
from clone_manager import clone_repository, cleanup_repository
from semgrep_runner import run_semgrep
from gitleaks_runner import run_gitleaks
from checkov_runner import run_checkov
from trivy_runner import run_trivy
from risk_engine import assess_risk
from persistence import update_scan_with_results, mark_scan_failed
from queue_client import get_connection, SCAN_REQUESTS_QUEUE as QUEUE_NAME

engine = get_engine(os.environ["DATABASE_URL"])
init_db(engine)


def process_scan(scan_id: int, repo_url: str, org_id: int) -> None:
    """
    Exécute le pipeline complet pour UN scan : clone, 4 scanners, score,
    mise à jour en base. Ne relance jamais d'exception vers l'appelant —
    toute erreur est capturée et se traduit par un mark_scan_failed, pour
    que le Worker continue de tourner même si un scan individuel plante.
    """
    session = get_session(engine)

    try:
        existing = session.query(Scan).filter(Scan.id == scan_id).first()
        if existing is None:
            print(f"⚠️  Scan {scan_id} introuvable en base, message ignoré")
            return
        if existing.status in ("completed", "failed"):
            print(f"⚠️  Scan {scan_id} déjà traité (status={existing.status}), message ignoré")
            return

        print(f"🔍 Traitement du scan {scan_id} : {repo_url}")

        clone_result = clone_repository(repo_url)
        if not clone_result.success:
            mark_scan_failed(session, scan_id, f"Échec du clonage : {clone_result.error_message}")
            print(f"❌ Scan {scan_id} : échec du clonage")
            return

        try:
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

            if not any([semgrep_result, gitleaks_result, checkov_result, trivy_result]):
                mark_scan_failed(session, scan_id, "Tous les scanners ont échoué, aucun résultat exploitable")
                print(f"❌ Scan {scan_id} : tous les scanners ont échoué")
                return

            assessment = assess_risk(semgrep_result, gitleaks_result, checkov_result, trivy_result)
            update_scan_with_results(
                session, scan_id, assessment,
                semgrep_result, gitleaks_result, checkov_result, trivy_result,
            )
            print(f"✅ Scan {scan_id} terminé : score={assessment.score}, classification={assessment.classification}")

        finally:
            cleanup_repository(clone_result.local_path)

    except Exception as e:
        print(f"❌ Scan {scan_id} : erreur inattendue — {e}")
        try:
            mark_scan_failed(session, scan_id, f"Erreur inattendue : {e}")
        except Exception:
            pass

    finally:
        session.close()


def on_message(channel, method, properties, body):
    """Callback pika appelé à chaque message reçu de la queue."""
    try:
        data = json.loads(body)
        process_scan(data["scan_id"], data["repo_url"], data["org_id"])
    finally:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    while True:
        connection = None

        try:
            print("🔄 Connexion à RabbitMQ...")

            connection = get_connection()

            channel = connection.channel()
            channel.queue_declare(
                queue=QUEUE_NAME,
                durable=True
            )

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=on_message
            )

            print(
                f"👷 Worker démarré, en écoute sur la queue "
                f"'{QUEUE_NAME}'... (Ctrl+C pour arrêter)"
            )

            channel.start_consuming()

        except KeyboardInterrupt:
            print("\n👋 Arrêt du Worker")
            break

        except Exception as e:
            print(f"❌ Erreur RabbitMQ : {e}")
            print("🔄 Nouvelle tentative dans 5 secondes...")
            time.sleep(5)

        finally:
            if connection is not None:
                try:
                    if connection.is_open:
                        connection.close()
                except Exception:
                    pass
if __name__ == "__main__":
    main()

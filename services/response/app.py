"""
app.py — Response Service

Consomme la queue "falco.response" (priorités critical, filtré en amont par
RabbitMQ) et met en quarantaine le pod incriminé plutôt que de l'isoler à
l'aveugle :

  1. Lit dynamiquement le vrai sélecteur du Deployment parent du pod
     (Pod -> ReplicaSet -> Deployment, spec.selector.matchLabels), quel
     que soit son nom de label - pas supposé être "app" en dur
  2. Retire ces labels de sélection du pod compromis (sauvegardés en
     annotation) et lui ajoute "secureops.io/quarantined=true"
  3. Le Deployment détecte qu'il manque un pod avec ses labels attendus
     et en recrée un sain automatiquement -> pas d'interruption de service
  4. Le Service arrête d'envoyer du trafic vers le pod compromis (il n'a
     plus les labels attendus)
  5. Une NetworkPolicy de quarantaine (une par namespace, idempotente)
     bloque tout ingress/egress pour tout pod portant le label de
     quarantaine -> confinement réseau
  6. Le pod compromis reste vivant (jamais supprimé) pour investigation
     forensique ; sa suppression ou sa réintégration est une décision
     humaine ultérieure, pas automatique

Garde-fous :
- whitelist stricte de règles autorisées à déclencher une mise en quarantaine
- exclusion des namespaces système (kube-system, argocd, external-secrets, falco)
- exclusion des pods d'infra critique via le label secureops.io/critical-infra
  (remplace l'ancienne exclusion globale du namespace "secureops", qui était
  trop large : ce namespace contient aussi de vrais workloads comme auth/worker
  qui doivent rester protégeables)
- rate limiting (max N mises en quarantaine/minute)
- RBAC minimal (ServiceAccount dédié, Role scopé aux namespaces ciblés)

Lancer avec : python3 app.py
"""

import json
import os
import time

from dotenv import load_dotenv

load_dotenv("../../.env")

import pika
from kubernetes import client, config
from kubernetes.client.rest import ApiException

RABBITMQ_URL = os.environ["RABBITMQ_URL"]

ALLOWED_RULES = {
    "terminal_shell_in_container",
    "reverse_shell",
    "write_below_etc",
}

# "secureops" retiré : ce namespace contient aussi de vrais services
# applicatifs (auth, worker) qui doivent pouvoir être mis en quarantaine.
# La protection de l'infra sécu elle-même (Falco, RabbitMQ, response) se
# fait maintenant via le label CRITICAL_INFRA_LABEL_KEY, pas par namespace.
EXCLUDED_NAMESPACES = {"kube-system", "argocd", "external-secrets", "falco"}

MAX_QUARANTINES_PER_MINUTE = 5
_quarantine_timestamps = []

QUARANTINE_LABEL_KEY = "secureops.io/quarantined"
QUARANTINE_NETPOL_NAME = "secureops-quarantine"

# Label à poser manuellement (dans les manifests de déploiement) sur les
# pods d'infra sécu : Falco, RabbitMQ, le service response lui-même.
# Ex. : kubectl label pod <pod> secureops.io/critical-infra=true
# Un pod portant ce label ne sera jamais mis en quarantaine, quel que soit
# son namespace.
CRITICAL_INFRA_LABEL_KEY = "secureops.io/critical-infra"

try:
    config.load_incluster_config()
    print("[response] config Kubernetes : in-cluster")
except config.ConfigException:
    config.load_kube_config()
    print("[response] config Kubernetes : kubeconfig local (mode dev)")

core_api = client.CoreV1Api()
net_api = client.NetworkingV1Api()
apps_api = client.AppsV1Api()


def rate_limit_ok() -> bool:
    now = time.time()
    _quarantine_timestamps[:] = [t for t in _quarantine_timestamps if now - t < 60]
    if len(_quarantine_timestamps) >= MAX_QUARANTINES_PER_MINUTE:
        return False
    _quarantine_timestamps.append(now)
    return True


def is_critical_infra(namespace: str, pod_name: str) -> bool:
    """Vérifie si le pod porte le label d'infra critique, ce qui l'exempte
    de toute mise en quarantaine automatique. En cas de doute (pod introuvable,
    erreur API), on considère le pod comme critique par précaution."""
    try:
        pod = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
    except ApiException as exc:
        print(f"[response] impossible de lire le pod '{pod_name}' dans '{namespace}' "
              f"({exc.status}) : traité comme infra critique par précaution")
        return True
    labels = pod.metadata.labels or {}
    return labels.get(CRITICAL_INFRA_LABEL_KEY) == "true"


def ensure_quarantine_networkpolicy(namespace: str) -> None:
    """Crée (si absente) la NetworkPolicy deny-all pour les pods en quarantaine
    dans ce namespace. Idempotent : ignore l'erreur si elle existe déjà."""
    policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(
            name=QUARANTINE_NETPOL_NAME,
            namespace=namespace,
            annotations={"secureops.io/purpose": "deny-all pour pods en quarantaine"},
        ),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(
                match_labels={QUARANTINE_LABEL_KEY: "true"}
            ),
            policy_types=["Ingress", "Egress"],
            ingress=[],
            egress=[],
        ),
    )
    try:
        net_api.create_namespaced_network_policy(namespace=namespace, body=policy)
        print(f"[response] NetworkPolicy de quarantaine créée dans '{namespace}'")
    except ApiException as exc:
        if exc.status == 409:
            pass  # déjà présente, rien à faire
        else:
            raise


def get_owner_selector_labels(namespace: str, pod) -> dict:
    """Remonte Pod -> ReplicaSet -> Deployment pour trouver les VRAIS labels
    de sélection utilisés par ce Deployment, quel que soit leur nom (pas
    supposé être "app"). Retourne {} si le pod n'appartient à aucun
    Deployment (pod nu, DaemonSet, StatefulSet non géré ici) - dans ce cas
    on n'efface aucun label, seule la NetworkPolicy isole le pod."""
    owner_refs = pod.metadata.owner_references or []
    rs_ref = next((o for o in owner_refs if o.kind == "ReplicaSet"), None)
    if not rs_ref:
        return {}

    try:
        rs = apps_api.read_namespaced_replica_set(name=rs_ref.name, namespace=namespace)
    except ApiException:
        return {}

    rs_owner_refs = rs.metadata.owner_references or []
    deploy_ref = next((o for o in rs_owner_refs if o.kind == "Deployment"), None)
    if not deploy_ref:
        return {}

    try:
        deploy = apps_api.read_namespaced_deployment(name=deploy_ref.name, namespace=namespace)
    except ApiException:
        return {}

    return dict(deploy.spec.selector.match_labels or {})


def quarantine_pod(namespace: str, pod_name: str, event_id: str, rule: str) -> None:
    pod = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
    current_labels = dict(pod.metadata.labels or {})

    if current_labels.get(QUARANTINE_LABEL_KEY) == "true":
        print(f"[response] pod '{pod_name}' déjà en quarantaine, rien à faire")
        return

    # Lit le VRAI sélecteur du Deployment parent (quel que soit son nom de
    # label), au lieu de supposer "app" en dur. Un merge patch n'efface une
    # clé que si on lui donne explicitement la valeur None ; l'omettre ne
    # l'efface pas.
    owner_selector_labels = get_owner_selector_labels(namespace, pod)

    patch_labels = {QUARANTINE_LABEL_KEY: "true"}
    for key in owner_selector_labels:
        if key in current_labels:
            patch_labels[key] = None

    body = {
        "metadata": {
            "labels": patch_labels,
            "annotations": {
                "secureops.io/event-id": event_id,
                "secureops.io/reason": rule,
                "secureops.io/quarantined-at": str(time.time()),
                "secureops.io/original-selector-labels": json.dumps(owner_selector_labels),
            },
        }
    }

    core_api.patch_namespaced_pod(name=pod_name, namespace=namespace, body=body)
    print(f"[response] pod '{pod_name}' mis en quarantaine dans '{namespace}' (event_id={event_id})")

    ensure_quarantine_networkpolicy(namespace)


def handle_message(channel, method, properties, body):
    event = json.loads(body)
    event_id = event.get("event_id")
    rule = event.get("rule", "")
    rule_slug = rule.lower().replace(" ", "_")
    output_fields = event.get("output_fields", {})
    namespace = output_fields.get("k8s.ns.name")
    pod_name = output_fields.get("k8s.pod.name")

    print(f"[response] reçu event_id={event_id} rule='{rule}' ns={namespace} pod={pod_name}")

    reasons_skipped = []
    if rule_slug not in ALLOWED_RULES:
        reasons_skipped.append(f"règle '{rule_slug}' non whitelistée")
    if namespace in EXCLUDED_NAMESPACES:
        reasons_skipped.append(f"namespace '{namespace}' exclu")
    if not namespace or not pod_name:
        reasons_skipped.append("namespace/pod manquant dans l'event")
    elif is_critical_infra(namespace, pod_name):
        reasons_skipped.append(f"pod marqué comme infra critique ({CRITICAL_INFRA_LABEL_KEY})")

    should_quarantine = not reasons_skipped
    if should_quarantine and not rate_limit_ok():
        should_quarantine = False
        reasons_skipped.append("rate limit atteint (protection contre effet domino)")

    if should_quarantine:
        try:
            quarantine_pod(namespace, pod_name, event_id, rule)
        except ApiException as exc:
            print(f"[response] ERREUR API K8s pour {event_id} : {exc}")
        except Exception as exc:
            print(f"[response] ERREUR inattendue pour {event_id} : {exc}")
    else:
        print(f"[response] alerte SANS action auto ({', '.join(reasons_skipped)}) : {event_id}")

    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="falco.response", on_message_callback=handle_message)
    print("[response] en écoute sur falco.response...")
    channel.start_consuming()


if __name__ == "__main__":
    main()

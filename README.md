# SecureOps

Plateforme SaaS DevSecOps qui centralise plusieurs outils de scan de sécurité (analyse statique, secrets, dépendances, infrastructure as code) derrière une API unique, avec calcul d'un score de risque exploitable.

**Statut actuel : Phase 1 & 2 du blueprint terminées** — pipeline de scan complet fonctionnel avec persistance et API REST.

## Problème résolu

Une équipe dev/sécu utilise généralement 5-6 outils différents (Semgrep, Trivy, Checkov, Gitleaks...) de façon manuelle et déconnectée. SecureOps centralise ces outils dans une seule plateforme qui répond à une question : *"Mon app est-elle prête à être déployée en toute sécurité ?"*

## Ce qui fonctionne aujourd'hui

- Clonage automatique d'un repo Git (shallow clone, détection de branche par défaut)
- 4 scanners intégrés en parallèle conceptuel :
  - **Semgrep** — analyse statique du code
  - **Gitleaks** — détection de secrets hardcodés
  - **Checkov** — mauvaises configurations Infrastructure as Code (Terraform)
  - **Trivy** — CVE connues dans les dépendances (mode filesystem)
- Normalisation des résultats des 4 scanners vers un vocabulaire commun
- Calcul d'un score de risque (0-100) et classification (Safe/Warning/Critical)
- Persistance PostgreSQL (historique des scans, détail des findings)
- API REST (FastAPI) : lancer un scan, lister l'historique, consulter le détail

## Architecture

```
Client HTTP
    │
    ▼
FastAPI (app.py)
    │
    ├── clone_manager.py    → clone le repo (shallow, branche auto-détectée)
    │
    ├── semgrep_runner.py   ─┐
    ├── gitleaks_runner.py   │
    ├── checkov_runner.py    ├─ 4 scanners, exécutés en subprocess
    ├── trivy_runner.py     ─┘
    │
    ├── normalize.py        → normalise chaque sévérité native vers
    │                          un vocabulaire commun (critical/high/medium/secret)
    │
    ├── risk_engine.py      → calcule le score (0-100) et la classification
    │
    └── persistence.py      → sauvegarde scan + findings en PostgreSQL
                               (models.py : tables `scans` et `findings`)
```

Ce découpage anticipe le passage en microservices (Phase 4 du blueprint) : chaque module a une responsabilité unique et sera facilement extractible dans son propre service.

## Stack technique

- **Backend** : Python 3.12, FastAPI, SQLAlchemy
- **Base de données** : PostgreSQL
- **Scanners** : Semgrep (pip), Gitleaks v8.21.2 (binaire), Checkov (pip), Trivy v0.74.0 (binaire)
- **Environnement de dev** : VM Ubuntu Desktop (VMware)

## Installation

```bash
# Environnement Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Binaires (Gitleaks et Trivy ne sont pas des paquets pip)
mkdir -p bin
# Gitleaks
curl -sL -o bin/gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz
tar -xzf bin/gitleaks.tar.gz -C bin gitleaks && rm bin/gitleaks.tar.gz && chmod +x bin/gitleaks
# Trivy
curl -sL -o bin/trivy.tar.gz https://github.com/aquasecurity/trivy/releases/download/v0.74.0/trivy_0.74.0_Linux-64bit.tar.gz
tar -xzf bin/trivy.tar.gz -C bin trivy && rm bin/trivy.tar.gz && chmod +x bin/trivy

# Base de données PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER secureops_user WITH PASSWORD 'change_moi';"
sudo -u postgres psql -c "CREATE DATABASE secureops_db OWNER secureops_user;"

# Variables d'environnement
cat > .env << 'EOF'
DATABASE_URL=postgresql://secureops_user:change_moi@localhost:5432/secureops_db
EOF
```

## Lancer l'API

```bash
cd services/scan
uvicorn app:app --reload --port 8000
```

Documentation interactive disponible sur `http://localhost:8000/docs`.

### Exemples d'utilisation

```bash
# Lancer un scan complet (synchrone, peut prendre 1-2 minutes)
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pallets/flask.git"}'

# Historique des scans
curl http://localhost:8000/scans

# Détail d'un scan précis
curl http://localhost:8000/scans/1
```

## Décisions de conception notables

Quelques choix volontaires, documentés ici pour éviter toute impression qu'ils sont accidentels :

- **Scanners installés localement (pas encore containerisés)** : la sandboxisation Docker par scan (isolation réseau, conteneur éphémère) est prévue en Phase 3-4. Séparer "faire fonctionner la logique" de "l'isoler proprement" a évité de déboguer deux problèmes à la fois.
- **Endpoint `/scan` synchrone** : le passage à un traitement asynchrone (RabbitMQ, tâches de fond) est prévu en Phase 4 avec le découpage en microservices, pas avant.
- **Normalisation des sévérités par scanner, dans des fonctions dédiées** (`normalize.py`) : chaque scanner a son propre vocabulaire de sévérité (Semgrep utilise ERROR/WARNING/INFO *et* parfois CRITICAL/HIGH/MEDIUM/LOW selon la catégorie de règle ; Trivy utilise le vocabulaire CVSS ; Checkov et Gitleaks n'ont pas de sévérité graduée en version gratuite). Une fonction de mapping par scanner permet de tester chaque cas isolément plutôt que de tout vérifier via un scan complet.
- **Checkov restreint au framework `terraform`** (`--framework terraform`) : la détection de secrets intégrée à Checkov fait doublon avec Gitleaks ; chaque scanner reste responsable d'un seul domaine pour éviter de compter deux fois le même problème dans le score.
- **Formule de scoring volontairement stricte** : `100 - 20×critical - 10×high - 3×medium - 15×secrets`. Sur un projet mature comme Flask (beaucoup de code d'exemple/documentation), le score tombe à 0 — ce n'est pas un bug, la formule est conservative par choix pour ce MVP et pourrait être pondérée différemment (ex: distinguer code source vs exemples) dans une itération future.

## Roadmap

- [x] **Phase 1** — MVP local : clone + Semgrep + Gitleaks + score
- [x] **Phase 2** — Persistance PostgreSQL, + Checkov + Trivy, API FastAPI complète
- [ ] **Phase 3** — Authentification (JWT, multi-organisation), Dashboard React
- [ ] **Phase 4** — Découpage en microservices, RabbitMQ, Notification Service
- [ ] **Phase 5** — Déploiement AWS (EKS/ECR/RDS...), CI/CD, observabilité (Falco, Argo CD, Prometheus/Grafana)
- [ ] **Phase 6** (post-v1) — Volet IA : explications de vulnérabilités en langage clair (LLM), puis suggestions de correction et remédiation assistée avec revue humaine obligatoire avant tout push Git

## Limitations connues du MVP

- Scanners exécutés sur l'hôte, pas encore isolés dans des conteneurs éphémères
- Pas d'authentification : tout scan est public, pas de notion d'organisation
- Endpoint de scan synchrone : une requête HTTP reste ouverte pendant toute la durée du scan
- Sévérité Checkov non graduée (limite de la version open-source de l'outil)

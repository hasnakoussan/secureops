"""
app.py — Phase 2 : API FastAPI du Scan Service

Expose le pipeline complet (clone -> 4 scanners -> score -> persistance)
via HTTP. Endpoint /scan volontairement SYNCHRONE pour cette phase : le
client attend la fin du scan (peut prendre 1-2 minutes). Le passage à un
mode asynchrone avec RabbitMQ est prévu en Phase 4 (découpage microservices),
pas avant — on évite d'introduire cette complexité avant d'en avoir besoin.

Lancer avec : uvicorn app:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
import json

from dotenv import load_dotenv

load_dotenv("../../.env")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
import jwt

from models import get_engine, init_db, get_session as get_db_session, Scan
from clone_manager import clone_repository, cleanup_repository
from semgrep_runner import run_semgrep
from gitleaks_runner import run_gitleaks
from checkov_runner import run_checkov
from trivy_runner import run_trivy
from risk_engine import assess_risk
from persistence import save_scan_result
from auth_verification import verify_access_token, TokenPayload

engine = get_engine(os.environ["DATABASE_URL"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # S'assure que les tables existent au démarrage de l'API, sans avoir
    # besoin d'une étape de migration séparée pour ce MVP.
    init_db(engine)
    yield


app = FastAPI(title="SecureOps — Scan Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()


def get_db():
    """
    Dependency FastAPI : fournit une session DB par requête, et la ferme
    proprement après (même en cas d'erreur), via le pattern try/finally.
    """
    session = get_db_session(engine)
    try:
        yield session
    finally:
        session.close()


def get_current_org(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenPayload:
    """
    Dependency FastAPI : valide le JWT et retourne son contenu (user_id,
    org_id, role). Utilise auth_verification.py, PAS d'appel réseau vers
    l'Auth Service (vérification stateless via le secret partagé).
    """
    token = credentials.credentials
    try:
        return verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


# --- Schémas Pydantic (validation des entrées/sorties de l'API) ---

class ScanRequest(BaseModel):
    repo_url: str = Field(..., description="URL du repo Git à scanner")


class FindingResponse(BaseModel):
    source: str
    rule_id: str
    file_path: str
    line: int
    severity: str | None
    message: str | None

    class Config:
        from_attributes = True  # permet de construire depuis un objet SQLAlchemy


class ScanSummaryResponse(BaseModel):
    id: int
    repo_url: str
    score: int | None
    classification: str | None
    status: str

    class Config:
        from_attributes = True


class ScanDetailResponse(ScanSummaryResponse):
    critical_count: int
    high_count: int
    medium_count: int
    secrets_count: int
    findings: list[FindingResponse]
    failed_scanners: list[str] = []

    @field_validator("failed_scanners", mode="before")
    @classmethod
    def parse_failed_scanners(cls, value):
        """
        Le champ est stocké en base comme une chaîne JSON (ex: '["trivy"]')
        ou None si tous les scanners ont réussi. On le convertit en liste
        Python ici, pour que l'API expose directement un tableau JSON
        exploitable côté frontend, sans que celui-ci ait à parser une
        chaîne imbriquée.
        """
        if value is None:
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value


# --- Endpoints ---

@app.post("/scan", response_model=ScanDetailResponse)
def create_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(get_current_org),
):
    """
    Lance un scan complet sur le repo donné : clone, exécute les 4
    scanners, calcule le score, persiste le résultat rattaché à
    l'organisation de l'utilisateur authentifié, et le retourne.

    ATTENTION : endpoint SYNCHRONE — la requête HTTP reste ouverte
    pendant toute la durée du scan (peut prendre 1-2 minutes).
    """
    clone_result = clone_repository(request.repo_url)
    if not clone_result.success:
        raise HTTPException(
            status_code=400,
            detail=f"Échec du clonage : {clone_result.error_message}",
        )

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
            raise HTTPException(
                status_code=502,
                detail="Tous les scanners ont échoué, aucun résultat exploitable",
            )

        assessment = assess_risk(semgrep_result, gitleaks_result, checkov_result, trivy_result)

        saved_scan = save_scan_result(
            db, token.org_id, request.repo_url, assessment,
            semgrep_result, gitleaks_result, checkov_result, trivy_result,
        )

        return saved_scan

    finally:
        cleanup_repository(clone_result.local_path)


@app.get("/scans", response_model=list[ScanSummaryResponse])
def list_scans(
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(get_current_org),
):
    """
    Liste les scans de l'organisation de l'utilisateur authentifié
    uniquement, du plus récent au plus ancien — c'est le filtrage
    multi-tenant prévu par le blueprint (section 2 : "toutes les
    requêtes vers les autres services sont filtrées par cet org_id").
    """
    return (
        db.query(Scan)
        .filter(Scan.org_id == token.org_id)
        .order_by(Scan.started_at.desc())
        .all()
    )


@app.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(get_current_org),
):
    """
    Détail complet d'un scan, avec tous ses findings — uniquement si le
    scan appartient à l'organisation de l'utilisateur authentifié.

    Note de sécurité importante : on filtre par org_id DANS la requête
    SQL elle-même (pas juste "chercher par id puis vérifier après"). Ça
    évite qu'un scan d'une autre organisation soit ne serait-ce que
    chargé en mémoire, et le comportement observable est identique que
    le scan n'existe pas OU qu'il appartienne à une autre organisation
    (404 dans les deux cas) — on ne révèle jamais "ce scan existe mais
    n'est pas à vous" (ça confirmerait l'existence d'IDs à un attaquant).
    """
    scan = (
        db.query(Scan)
        .filter(Scan.id == scan_id, Scan.org_id == token.org_id)
        .first()
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return scan


@app.get("/health")
def health_check():
    """Endpoint de santé basique, utile plus tard pour le monitoring/K8s."""
    return {"status": "ok"}

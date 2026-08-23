"""
app.py — Phase 4 : API FastAPI du Scan Service (asynchrone)

POST /scan ne fait plus le travail lui-même : il crée une ligne Scan
avec status="pending", publie un message dans RabbitMQ, et répond
IMMÉDIATEMENT (202 Accepted). Un processus séparé (worker.py) consomme
ce message et fait le vrai travail, puis met à jour la ligne Scan. Le
client doit sonder GET /scans/{id} jusqu'à voir status="completed" ou
"failed".

Lancer l'API avec : uvicorn app:app --reload --port 8000
Lancer le Worker séparément (autre terminal) : python3 worker.py
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
from persistence import create_pending_scan, mark_scan_failed
from queue_client import publish_scan_request
from auth_verification import verify_access_token, TokenPayload

engine = get_engine(os.environ["DATABASE_URL"])


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    session = get_db_session(engine)
    try:
        yield session
    finally:
        session.close()


def get_current_org(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenPayload:
    """Valide le JWT, vérification stateless (secret partagé, pas d'appel réseau)."""
    token = credentials.credentials
    try:
        return verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


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
        from_attributes = True


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
    error_message: str | None = None

    @field_validator("failed_scanners", mode="before")
    @classmethod
    def parse_failed_scanners(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value


@app.post("/scan", response_model=ScanDetailResponse, status_code=202)
def create_scan(
    request: ScanRequest,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(get_current_org),
):
    """
    Enregistre une demande de scan et répond IMMÉDIATEMENT (202 Accepted)
    — le vrai travail est fait de façon asynchrone par un Worker séparé.
    """
    scan = create_pending_scan(db, token.org_id, request.repo_url)

    try:
        publish_scan_request(scan_id=scan.id, repo_url=request.repo_url, org_id=token.org_id)
    except Exception as e:
        mark_scan_failed(db, scan.id, f"Impossible de publier la demande de scan : {e}")
        raise HTTPException(
            status_code=503,
            detail="Le service de traitement des scans est indisponible pour le moment",
        )

    return scan


@app.get("/scans", response_model=list[ScanSummaryResponse])
def list_scans(
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(get_current_org),
):
    """Liste les scans de l'organisation authentifiée uniquement (isolation multi-tenant)."""
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
    Détail d'un scan. C'est cet endpoint que le frontend interroge en
    boucle (polling) tant que status="pending".
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
    return {"status": "ok"}

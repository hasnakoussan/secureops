"""
app.py — Phase 2 : API FastAPI du Scan Service

Expose le pipeline complet (clone -> 4 scanners -> score -> persistance)
via HTTP. Endpoint /scan volontairement SYNCHRONE pour cette phase : le
client attend la fin du scan (peut prendre 1-2 minutes). Le passage à un
mode asynchrone avec RabbitMQ est prévu en Phase 4, pas avant.

Lancer avec : uvicorn app:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models import get_engine, init_db, get_session as get_db_session, Scan
from clone_manager import clone_repository, cleanup_repository
from semgrep_runner import run_semgrep
from gitleaks_runner import run_gitleaks
from checkov_runner import run_checkov
from trivy_runner import run_trivy
from risk_engine import assess_risk
from persistence import save_scan_result

load_dotenv("../../.env")

engine = get_engine(os.environ["DATABASE_URL"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(title="SecureOps — Scan Service", lifespan=lifespan)


def get_db():
    """Dependency FastAPI : fournit une session DB par requête."""
    session = get_db_session(engine)
    try:
        yield session
    finally:
        session.close()


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


@app.post("/scan", response_model=ScanDetailResponse)
def create_scan(request: ScanRequest, db: Session = Depends(get_db)):
    """
    Lance un scan complet : clone, 4 scanners, score, persistance.
    ATTENTION : endpoint SYNCHRONE, la requête reste ouverte 1-2 minutes.
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
            db, request.repo_url, assessment,
            semgrep_result, gitleaks_result, checkov_result, trivy_result,
        )

        return saved_scan

    finally:
        cleanup_repository(clone_result.local_path)


@app.get("/scans", response_model=list[ScanSummaryResponse])
def list_scans(db: Session = Depends(get_db)):
    """Liste tous les scans effectués, du plus récent au plus ancien."""
    return db.query(Scan).order_by(Scan.started_at.desc()).all()


@app.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """Détail complet d'un scan, avec tous ses findings."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return scan


@app.get("/health")
def health_check():
    """Endpoint de santé basique, utile plus tard pour le monitoring/K8s."""
    return {"status": "ok"}

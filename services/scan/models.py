"""
models.py — Phase 4 : modèles SQLAlchemy pour la persistance (asynchrone)

Deux tables :
  - scans : une ligne par scan effectué. Cycle de vie du statut :
            "pending" (créé par l'API) -> "completed"/"failed" (mis à
            jour par le Worker une fois le traitement terminé)
  - findings : une ligne par vulnérabilité individuelle détectée
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Scan(Base):
    """Un scan effectué sur un repo, avec son résumé de score."""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, nullable=False)
    repo_url = Column(String, nullable=False)
    score = Column(Integer, nullable=True)
    classification = Column(String, nullable=True)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    secrets_count = Column(Integer, default=0)
    status = Column(String, default="pending")        # "pending", "completed", "failed"
    failed_scanners = Column(Text, nullable=True)      # JSON list, ex: '["trivy"]' — échec partiel
    error_message = Column(Text, nullable=True)        # rempli seulement si le scan a ÉCHOUÉ ENTIÈREMENT
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    """Une vulnérabilité individuelle détectée pendant un scan."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    source = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    line = Column(Integer, nullable=False)
    severity = Column(String, nullable=True)
    message = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")


def get_engine(database_url: str):
    return create_engine(database_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

"""
models.py — Phase 2 : modèles SQLAlchemy pour la persistance

Deux tables :
  - scans : une ligne par scan effectué (résumé + score)
  - findings : une ligne par vulnérabilité individuelle détectée,
               rattachée à un scan via scan_id (relation 1-to-many)
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Scan(Base):
    """Un scan effectué sur un repo, avec son résumé de score."""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True)
    repo_url = Column(String, nullable=False)
    score = Column(Integer, nullable=True)
    classification = Column(String, nullable=True)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    secrets_count = Column(Integer, default=0)
    status = Column(String, default="running")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Finding(Base):
    """Une vulnérabilité individuelle détectée pendant un scan."""
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    source = Column(String, nullable=False)     # "semgrep" ou "gitleaks"
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


if __name__ == "__main__":
    engine = get_engine("sqlite:///test_secureops.db")
    init_db(engine)
    session = get_session(engine)

    scan = Scan(
        repo_url="https://github.com/pallets/flask.git",
        score=0,
        classification="Critical",
        critical_count=0,
        high_count=15,
        medium_count=0,
        secrets_count=6,
        status="completed",
    )
    scan.findings.append(Finding(
        source="semgrep", rule_id="django-no-csrf-token",
        file_path="templates/index.html", line=14,
        severity="WARNING", message="Django csrf_token not found",
    ))
    scan.findings.append(Finding(
        source="gitleaks", rule_id="generic-api-key",
        file_path="docs/config.rst", line=41,
        severity=None, message=None,
    ))

    session.add(scan)
    session.commit()

    print(f"✅ Scan créé avec id={scan.id}")
    retrieved = session.query(Scan).filter_by(id=scan.id).first()
    print(f"✅ Scan relu : {retrieved.repo_url}, score={retrieved.score}")
    print(f"✅ {len(retrieved.findings)} findings liés :")
    for f in retrieved.findings:
        print(f"   [{f.source}] {f.rule_id} — {f.file_path}:{f.line}")

    session.close()

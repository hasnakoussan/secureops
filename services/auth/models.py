"""
models.py — Phase 3 : modèles SQLAlchemy de l'Auth Service

Deux tables, indépendantes des tables scans/findings du Scan Service :
  - organizations : une organisation cliente (modèle SaaS multi-tenant)
  - users : les membres d'une organisation, avec un rôle

Voir blueprint section 3.1.

Note d'architecture : ce fichier utilise sa PROPRE instance Base (déclarée
ici, pas importée de services/scan/models.py). Même si les deux services
partagent la même base de données PostgreSQL pour l'instant (Phase 3),
chaque service reste responsable de la définition de SES tables — ça évite
un couplage entre services qui devra de toute façon disparaître en Phase 4
(bases de données séparées par microservice).
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Role(str, enum.Enum):
    """Rôles possibles d'un utilisateur au sein de son organisation."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    """Une organisation cliente (modèle SaaS multi-tenant)."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    plan = Column(String, default="free")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    """Un utilisateur, membre d'une organisation."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.MEMBER, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="users")


def get_engine(database_url: str):
    return create_engine(database_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

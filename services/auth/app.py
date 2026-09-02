"""
app.py — Phase 3 : API FastAPI de l'Auth Service

Endpoints (blueprint section 3.1) :
    POST /auth/register — crée une organisation + son premier utilisateur (owner)
    POST /auth/login     — vérifie email/mot de passe, retourne access + refresh token
    GET  /auth/me        — infos de l'utilisateur courant (à partir du JWT)
    POST /auth/refresh   — renouvelle l'access token à partir d'un refresh token

Service SÉPARÉ du Scan Service : sa propre app FastAPI, son propre port
(8001, le Scan Service étant sur 8000), sa propre base de données.

Lancer avec : uvicorn app:app --reload --port 8001
"""

import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv

# IMPORTANT : load_dotenv() doit s'exécuter AVANT l'import de security.py,
# car ce module lit JWT_SECRET depuis l'environnement au moment de l'import
# (variable de module, pas relue à chaque appel). Si l'ordre est inversé,
# security.JWT_SECRET reste None même après le chargement du .env — bug
# découvert en testant, pas une supposition théorique.
load_dotenv("../../.env")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import jwt

from models import get_engine, init_db, get_session as get_db_session, Organization, User, Role
from security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

engine = get_engine(os.environ["AUTH_DATABASE_URL"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield


app = FastAPI(title="SecureOps — Auth Service", lifespan=lifespan)

# CORS : autorise le dashboard React (dev server sur localhost:5173) à
# appeler cette API depuis le navigateur. En production, on restreindrait
# allow_origins au vrai domaine du dashboard plutôt que localhost.
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency FastAPI : extrait et valide le JWT du header Authorization,
    retourne l'utilisateur correspondant.

    Centraliser cette logique ici (plutôt que la dupliquer dans chaque
    endpoint protégé) garantit que TOUS les endpoints qui en dépendent
    appliquent exactement la même vérification.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Ce token n'est pas un access token")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    return user


# --- Schémas Pydantic ---

class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=1, description="Nom de l'organisation à créer")
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 caractères")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., description="admin, member, ou viewer (pas owner)")


class InviteResponse(BaseModel):
    email: str
    role: str
    org_id: int
    temporary_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    org_id: int
    org_name: str

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """
    Version allégée de UserResponse pour lister les membres d'une
    organisation — pas besoin de répéter org_id/org_name pour chaque
    ligne d'une liste qui appartient déjà à une seule organisation.
    """
    id: int
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Crée une nouvelle organisation ET son premier utilisateur (role owner)
    en une seule opération — un utilisateur ne peut pas exister sans
    organisation dans ce modèle de données (org_id est NOT NULL).
    """
    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")

    org = Organization(name=request.org_name)
    org.users.append(User(
        email=request.email,
        password_hash=hash_password(request.password),
        role=Role.OWNER,
    ))
    db.add(org)
    db.commit()

    user = org.users[0]
    access_token = create_access_token(user_id=user.id, org_id=org.id, role=user.role.value)
    refresh_token = create_refresh_token(user_id=user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Vérifie email/mot de passe, retourne un nouveau couple de tokens."""
    user = db.query(User).filter(User.email == request.email).first()

    # Note volontaire : le message d'erreur est IDENTIQUE que ce soit
    # l'email qui n'existe pas ou le mot de passe qui est faux. Révéler
    # "cet email n'existe pas" permettrait à un attaquant de vérifier
    # quels emails sont enregistrés (énumération de comptes).
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role.value)
    refresh_token = create_refresh_token(user_id=user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retourne les infos de l'utilisateur authentifié."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        org_id=current_user.org_id,
        org_name=current_user.organization.name,
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    """
    Échange un refresh token valide contre un nouveau couple access+refresh.

    On régénère aussi un nouveau refresh token (pas juste l'access token) :
    pattern de "rotation" qui limite la fenêtre d'exploitation si un
    refresh token venait à fuiter.
    """
    try:
        payload = decode_token(request.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expiré, reconnexion nécessaire")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Ce token n'est pas un refresh token")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    access_token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role.value)
    new_refresh_token = create_refresh_token(user_id=user.id)

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/auth/users", response_model=list[MemberResponse])
def list_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Liste les membres de l'organisation de l'utilisateur authentifié.

    Décision produit explicite : accessible à TOUS les membres de
    l'organisation (owner, admin, member, viewer), contrairement à
    /auth/invite qui reste restreint à owner/admin. Voir qui fait partie
    de son organisation est jugé être une information ouverte à toute
    l'équipe ; seule l'action d'INVITER de nouveaux membres est restreinte.
    """
    return (
        db.query(User)
        .filter(User.org_id == current_user.org_id)
        .order_by(User.created_at.desc())
        .all()
    )


@app.post("/api/auth/invite", response_model=InviteResponse, status_code=201)
def invite(
    request: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invite un nouveau membre dans l'organisation de l'utilisateur courant.

    Limite MVP assumée : pas de Notification Service encore construit
    (blueprint section 3.6, prévu en Phase 4) pour envoyer un vrai email
    d'invitation. On génère donc un mot de passe temporaire et on le
    retourne directement dans la réponse API — à transmettre manuellement
    à la personne invitée pour l'instant. Un vrai produit enverrait un
    email avec un lien d'activation à durée limitée, pas un mot de passe
    en clair dans une réponse API.
    """
    if current_user.role not in (Role.OWNER, Role.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Seuls les owners et admins peuvent inviter des membres",
        )

    if request.role not in ("admin", "member", "viewer"):
        raise HTTPException(
            status_code=400,
            detail="Le rôle doit être admin, member, ou viewer",
        )

    existing = db.query(User).filter(User.email == request.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")

    temporary_password = secrets.token_urlsafe(12)

    new_user = User(
        org_id=current_user.org_id,
        email=request.email,
        password_hash=hash_password(temporary_password),
        role=Role(request.role),
    )
    db.add(new_user)
    db.commit()

    return InviteResponse(
        email=new_user.email,
        role=new_user.role.value,
        org_id=new_user.org_id,
        temporary_password=temporary_password,
    )

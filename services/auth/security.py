"""
security.py — Phase 3 : hashing de mot de passe et gestion des JWT

Deux responsabilités séparées volontairement dans un module dédié
(plutôt que mélangées dans les endpoints) : le hashing et la génération
de tokens sont des opérations sensibles, les isoler facilite les tests
et réduit le risque d'erreur en les dupliquant ailleurs par accident.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(plain_password: str) -> str:
    """Hash un mot de passe en clair avec bcrypt (jamais stocké en clair)."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Vérifie qu'un mot de passe en clair correspond au hash stocké."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, org_id: int, role: str) -> str:
    """
    Crée un access token JWT de courte durée.

    Le payload contient user_id, org_id et role — c'est ce qui permettra
    aux AUTRES services (Scan, Report...) de filtrer leurs données par
    organisation sans avoir à interroger l'Auth Service à chaque requête
    (blueprint section 3.1 : "chaque requête inclut l'org_id dans le JWT").
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET n'est pas défini dans l'environnement")

    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Crée un refresh token JWT de longue durée.

    Contient volontairement MOINS d'informations que l'access token
    (juste l'identité de l'utilisateur, pas org_id/role) : son seul rôle
    est de permettre d'obtenir un nouvel access token via /auth/refresh,
    pas d'être utilisé directement pour accéder à des ressources.
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET n'est pas défini dans l'environnement")

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Décode et valide un token JWT (access ou refresh).

    Lève jwt.ExpiredSignatureError si le token a expiré, ou
    jwt.InvalidTokenError pour toute autre raison.
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET n'est pas défini dans l'environnement")

    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

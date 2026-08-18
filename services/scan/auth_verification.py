"""
auth_verification.py — Phase 3 : vérification JWT côté Scan Service

Ce module NE GÉNÈRE PAS de tokens (c'est le rôle de l'Auth Service) — il
sait seulement les DÉCODER et les VALIDER, via le même JWT_SECRET partagé.

Pattern standard de vérification JWT "stateless" en microservices : le
Scan Service authentifie une requête sans jamais appeler l'Auth Service
par le réseau, tant qu'il connaît le secret de signature. Le Scan Service
continue donc de fonctionner même si l'Auth Service est indisponible.

Contrepartie assumée : une révocation immédiate de token (ex: utilisateur
banni) ne serait pas détectée avant l'expiration naturelle (30 min) — une
vraie révocation nécessiterait une liste noire partagée, hors scope MVP.
"""

import os

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = "HS256"


class TokenPayload:
    """Représente les informations extraites d'un access token valide."""
    def __init__(self, user_id: int, org_id: int, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role


def verify_access_token(token: str) -> TokenPayload:
    """Décode et valide un access token JWT."""
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET n'est pas défini dans l'environnement")

    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Ce token n'est pas un access token")

    return TokenPayload(
        user_id=int(payload["sub"]),
        org_id=payload["org_id"],
        role=payload["role"],
    )

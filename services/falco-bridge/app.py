"""
app.py — Falco Bridge Service

Reçoit les webhooks de Falcosidekick (alertes runtime Falco depuis EKS),
vérifie un secret partagé, normalise l'event, et le publie sur RabbitMQ
(exchange "falco.events") pour consommation par notification-service et
response-service.

Service SÉPARÉ, son propre port (8006).

Lancer avec : uvicorn app:app --reload --port 8006
"""

import hmac
import json
import os
import time
import uuid

from dotenv import load_dotenv

load_dotenv("../../.env")

import pika
from fastapi import FastAPI, HTTPException, Request

FALCO_WEBHOOK_SECRET = os.environ["FALCO_WEBHOOK_SECRET"]
RABBITMQ_URL = os.environ["RABBITMQ_URL"]

app = FastAPI()


def verify_shared_secret(provided: str) -> bool:
    return hmac.compare_digest(provided, FALCO_WEBHOOK_SECRET)


def publish_event(routing_key: str, payload: dict) -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.basic_publish(
        exchange="falco.events",
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,
            message_id=payload["event_id"],
            content_type="application/json",
        ),
    )
    connection.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/falco/webhook")
async def falco_webhook(request: Request):
    provided_secret = request.headers.get("X-Falco-Shared-Secret", "")
    if not verify_shared_secret(provided_secret):
        raise HTTPException(status_code=401, detail="invalid shared secret")

    try:
        raw = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    priority = str(raw.get("priority", "unknown")).lower()
    rule = raw.get("rule", "unknown")
    rule_slug = rule.lower().replace(" ", "_")

    event = {
        "event_id": str(uuid.uuid4()),
        "received_at": time.time(),
        "priority": priority,
        "rule": rule,
        "output": raw.get("output"),
        "output_fields": raw.get("output_fields", {}),
    }

    routing_key = f"falco.{priority}.{rule_slug}"
    publish_event(routing_key, event)

    return {"status": "queued", "event_id": event["event_id"]}

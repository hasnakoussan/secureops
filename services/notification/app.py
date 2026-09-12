"""
app.py — Notification Service

Consomme la queue "falco.notifications" et envoie chaque alerte vers Slack
ET par email (AWS SES), en parallèle — pour éviter un point de défaillance
unique. Le message n'est acquitté que si au moins un des deux canaux réussit.

Lancer avec : python3 app.py
"""

import json
import os

from dotenv import load_dotenv

load_dotenv("../../.env")

import boto3
import pika
import requests
from botocore.exceptions import ClientError

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SES_SENDER_EMAIL = os.environ["SES_SENDER_EMAIL"]
SES_RECIPIENT_EMAIL = os.environ["SES_RECIPIENT_EMAIL"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

ses_client = boto3.client("ses", region_name=AWS_REGION)

PRIORITY_EMOJI = {
    "emergency": "🚨", "alert": "🚨", "critical": "🔴",
    "error": "🟠", "warning": "🟡", "notice": "🔵",
    "informational": "⚪", "debug": "⚪",
}


def send_to_slack(event: dict) -> None:
    priority = event.get("priority", "unknown")
    emoji = PRIORITY_EMOJI.get(priority, "⚪")
    text = (
        f"{emoji} *{priority.upper()}* — {event.get('rule')}\n"
        f"> {event.get('output')}\n"
        f"`event_id: {event.get('event_id')}`"
    )
    response = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
    response.raise_for_status()


def send_email(event: dict) -> None:
    priority = event.get("priority", "unknown").upper()
    subject = f"[SecureOps][{priority}] {event.get('rule')}"
    body = (
        f"Priorité : {priority}\n"
        f"Règle : {event.get('rule')}\n"
        f"Détails : {event.get('output')}\n"
        f"Event ID : {event.get('event_id')}\n"
    )
    ses_client.send_email(
        Source=SES_SENDER_EMAIL,
        Destination={"ToAddresses": [SES_RECIPIENT_EMAIL]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    )


def handle_message(channel, method, properties, body):
    event = json.loads(body)
    event_id = event.get("event_id")
    print(f"[notification] reçu event_id={event_id} priority={event.get('priority')}")

    slack_ok = False
    email_ok = False

    try:
        send_to_slack(event)
        slack_ok = True
        print(f"[notification] envoyé vers Slack : {event_id}")
    except Exception as exc:
        print(f"[notification] ERREUR Slack pour {event_id} : {exc}")

    try:
        send_email(event)
        email_ok = True
        print(f"[notification] envoyé par email : {event_id}")
    except ClientError as exc:
        print(f"[notification] ERREUR SES pour {event_id} : {exc}")
    except Exception as exc:
        print(f"[notification] ERREUR email inattendue pour {event_id} : {exc}")

    if slack_ok or email_ok:
        channel.basic_ack(delivery_tag=method.delivery_tag)
    else:
        print(f"[notification] ÉCHEC des DEUX canaux pour {event_id}, envoi en DLQ")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="falco.notifications", on_message_callback=handle_message)
    print("[notification] en écoute sur falco.notifications...")
    channel.start_consuming()


if __name__ == "__main__":
    main()

"""
app.py — Notification Service

Consomme la queue "falco.notifications" et envoie chaque alerte vers Slack.
(l'email/SES sera ajouté dans un second temps)

Lancer avec : python3 app.py
"""

import json
import os

from dotenv import load_dotenv

load_dotenv("../../.env")

import pika
import requests

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

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


def handle_message(channel, method, properties, body):
    event = json.loads(body)
    print(f"[notification] reçu event_id={event.get('event_id')} priority={event.get('priority')}")
    try:
        send_to_slack(event)
        print(f"[notification] envoyé vers Slack : {event.get('event_id')}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        print(f"[notification] ERREUR envoi Slack pour {event.get('event_id')} : {exc}")
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

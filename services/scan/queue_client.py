"""
queue_client.py — Client RabbitMQ pour la communication asynchrone.
"""

import os
import json

import pika

SCAN_REQUESTS_QUEUE = "scan_requests"


def get_connection() -> pika.BlockingConnection:
    """
    Ouvre une connexion à RabbitMQ avec les paramètres du container.
    """
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASSWORD", "guest")

    credentials = pika.PlainCredentials(user, password)

    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            credentials=credentials,
            heartbeat=600,
        )
    )


def publish_scan_request(scan_id: int, repo_url: str, org_id: int) -> None:
    """
    Publie un message scan_requested dans RabbitMQ.
    """
    connection = get_connection()

    try:
        channel = connection.channel()
        channel.queue_declare(queue=SCAN_REQUESTS_QUEUE, durable=True)

        message = json.dumps({
            "scan_id": scan_id,
            "repo_url": repo_url,
            "org_id": org_id,
        })

        channel.basic_publish(
            exchange="",
            routing_key=SCAN_REQUESTS_QUEUE,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()


if __name__ == "__main__":
    publish_scan_request(
        scan_id=999,
        repo_url="https://github.com/test/repo.git",
        org_id=1,
    )
    print("✅ Message de test publié dans la queue")

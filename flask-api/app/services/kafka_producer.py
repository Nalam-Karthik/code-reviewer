# flask-api/app/services/kafka_producer.py

import os
import json
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

# Kafka topic name — consumer listens on this same topic
REVIEW_TOPIC = "review.submitted"

# Producer is created once and reused
# value_serializer converts Python dict → JSON bytes automatically
_producer = None


def get_producer():
    """
    Lazy initialisation — only connect to Kafka when first needed.
    This prevents startup crashes if Kafka isn't ready yet.
    """
    global _producer
    if _producer is None:
        servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        _producer = KafkaProducer(
            bootstrap_servers=servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # Retry up to 3 times if publish fails
            retries=3,
        )
    return _producer


def publish_review_event(review_id: int, user_id: int, language: str, score: int):
    """
    Publish a review.submitted event to Kafka.

    The audit consumer reads this and writes to the audit_log table.
    Flask does NOT wait for the consumer — this is fire-and-forget.

    Args:
        review_id: the MySQL review ID just created
        user_id:   who submitted it
        language:  python, javascript, etc
        score:     AI severity score 0-100
    """
    event = {
        "review_id": review_id,
        "user_id":   user_id,
        "language":  language,
        "score":     score,
        "event_type": "review.submitted"
    }

    try:
        producer = get_producer()
        future   = producer.send(REVIEW_TOPIC, value=event)
        producer.flush()  # ensure the message actually gets sent
        logger.info(f"Published review event: review_id={review_id}")
        return True
    except KafkaError as e:
        # Don't crash the API if Kafka is down — just log it
        # The review is already saved in MySQL, Kafka is bonus
        logger.warning(f"Failed to publish Kafka event: {e}")
        return False
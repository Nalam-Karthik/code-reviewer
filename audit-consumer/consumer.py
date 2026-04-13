# audit-consumer/consumer.py
#
# This service runs forever in its own container.
# It reads from the review.submitted Kafka topic
# and writes an audit log row to MySQL.
#
# Key concept: Flask (producer) and this consumer are
# completely decoupled. Flask doesn't know or care
# whether this consumer is running.

import os
import json
import time
import logging
import mysql.connector
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
REVIEW_TOPIC  = "review.submitted"
GROUP_ID      = "audit-consumer-group"


def get_db_connection():
    """Connect to MySQL. Retries until successful."""
    while True:
        try:
            conn = mysql.connector.connect(
                host     = os.getenv("DB_HOST", "mysql"),
                port     = int(os.getenv("DB_PORT", "3306")),
                database = os.getenv("DB_NAME", "code_reviewer"),
                user     = os.getenv("DB_USER"),
                password = os.getenv("DB_PASSWORD"),
            )
            logger.info("Connected to MySQL")
            return conn
        except Exception as e:
            logger.warning(f"MySQL not ready yet: {e} — retrying in 5s")
            time.sleep(5)


def ensure_audit_table(conn):
    """
    Create the audit_log table if it doesn't exist.
    We create it here instead of Alembic because this
    is a separate service with its own DB responsibility.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            event_type  VARCHAR(100) NOT NULL,
            review_id   INT,
            user_id     INT,
            language    VARCHAR(50),
            score       INT,
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    logger.info("audit_log table ready")


def get_kafka_consumer():
    """Connect to Kafka. Retries until broker is available."""
    while True:
        try:
            consumer = KafkaConsumer(
                REVIEW_TOPIC,
                bootstrap_servers = KAFKA_SERVERS,
                group_id          = GROUP_ID,
                # Deserialise JSON bytes → Python dict automatically
                value_deserializer = lambda m: json.loads(m.decode("utf-8")),
                # Start from earliest message if this consumer is new
                auto_offset_reset  = "earliest",
                enable_auto_commit = True,
            )
            logger.info(f"Connected to Kafka, listening on topic: {REVIEW_TOPIC}")
            return consumer
        except NoBrokersAvailable:
            logger.warning("Kafka not ready yet — retrying in 5s")
            time.sleep(5)


def write_audit_log(conn, event: dict):
    """Write one audit row to MySQL."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (event_type, review_id, user_id, language, score)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        event.get("event_type", "review.submitted"),
        event.get("review_id"),
        event.get("user_id"),
        event.get("language"),
        event.get("score"),
    ))
    conn.commit()
    cursor.close()
    logger.info(f"Audit log written: review_id={event.get('review_id')}")


def main():
    logger.info("Audit consumer starting...")

    # Wait for dependencies
    db_conn  = get_db_connection()
    ensure_audit_table(db_conn)
    consumer = get_kafka_consumer()

    logger.info("Listening for review events...")

    # This loop runs forever — reads one message at a time
    for message in consumer:
        try:
            event = message.value
            logger.info(f"Received event: {event}")
            write_audit_log(db_conn, event)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reconnect to DB if connection dropped
            try:
                db_conn = get_db_connection()
            except Exception:
                pass


if __name__ == "__main__":
    main()
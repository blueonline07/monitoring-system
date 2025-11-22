"""
Kafka Producer - Forwards data to Kafka topics
"""

import socket
import json
from datetime import datetime
from confluent_kafka import Producer

from shared.config import KafkaTopics


class KafkaProducerService:
    """Kafka producer for forwarding monitoring data"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "security.protocol": "PLAINTEXT",
            "client.id": socket.gethostname(),
        })

    def send_monitoring_data(self, agent_id: str, timestamp: int, metrics: dict, metadata: dict) -> bool:
        """Forward monitoring data to Kafka"""
        try:
            self.producer.produce(
                KafkaTopics.MONITORING_DATA,
                key=agent_id.encode("utf-8"),
                value=json.dumps({
                    "agent_id": agent_id,
                    "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                    "metrics": metrics,
                    "metadata": metadata,
                }).encode("utf-8"),
            )
            self.producer.poll(0)
            return True
        except Exception:
            return False

    def close(self):
        """Close the producer"""
        self.producer.flush()

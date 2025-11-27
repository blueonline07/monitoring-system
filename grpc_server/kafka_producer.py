"""
Kafka Producer - Forwards data to Kafka topics
"""

import os
import socket
import json
from datetime import datetime
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

from shared.config import KafkaTopics


class KafkaProducerService:
    """Kafka producer for forwarding monitoring data"""

    def __init__(self, bootstrap_servers: str = None):
        if bootstrap_servers is None:
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.bootstrap_servers = bootstrap_servers

        # Create admin client for topic management and producer for publishing
        self.admin_client = AdminClient({"bootstrap.servers": bootstrap_servers})

        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "security.protocol": "PLAINTEXT",
            "client.id": socket.gethostname(),
        })

        # Optionally auto-create default topics used by the application
        try:
            create_topics = os.getenv("KAFKA_CREATE_TOPICS", "true").lower() in ("1", "true", "yes")
            if create_topics:
                default_partitions = int(os.getenv("KAFKA_DEFAULT_PARTITIONS", "3"))
                default_replication = int(os.getenv("KAFKA_DEFAULT_REPLICATION_FACTOR", "2"))
                self._ensure_topic_exists(
                    KafkaTopics.MONITORING_DATA, default_partitions, default_replication
                )
        except Exception as e:
            # Non-fatal: log and continue. Topic may already exist or cluster may not allow creation.
            print(f"⚠ Could not auto-create topics: {e}")

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

    def _ensure_topic_exists(self, topic_name: str, partitions: int = 1, replication: int = 1):
        """Create topic if it doesn't exist.

        Uses AdminClient.create_topics. If replication > available brokers the call may fail;
        this method will catch and report the error but won't raise.
        """
        # Check existing topics
        try:
            md = self.admin_client.list_topics(timeout=5)
            if topic_name in md.topics and md.topics[topic_name].err is None:
                # Topic exists
                return
        except Exception:
            # If we can't list topics, skip creation attempt
            print("⚠ Could not list topics from cluster; skipping topic creation check")
            return

        new_topic = NewTopic(topic=topic_name, num_partitions=partitions, replication_factor=replication)
        fs = self.admin_client.create_topics([new_topic], request_timeout=15)

        # Wait for operation results
        for topic, f in fs.items():
            try:
                f.result()  # raises on failure
                print(f"✓ Created topic '{topic}' (partitions={partitions}, replication={replication})")
            except Exception as e:
                # Common failure: replication factor > available brokers
                print(f"⚠ Failed to create topic '{topic}': {e}")

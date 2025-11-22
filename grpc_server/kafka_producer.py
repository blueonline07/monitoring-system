"""
Kafka Producer - Handles message production to Kafka topics
"""

import socket
import json
from datetime import datetime
from typing import Optional
from confluent_kafka import Producer

from shared.kafka_schemas import KafkaTopics


class KafkaProducerService:
    """Kafka producer service for forwarding monitoring data"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        Initialize Kafka producer

        Args:
            bootstrap_servers: Kafka bootstrap servers address
        """
        self.bootstrap_servers = bootstrap_servers
        self.producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "security.protocol": "PLAINTEXT",
                "client.id": socket.gethostname(),
            }
        )
        print(f"✓ Kafka producer initialized (bootstrap: {bootstrap_servers})")

    def send_monitoring_data(
        self,
        agent_id: str,
        timestamp: int,
        metrics: dict,
        metadata: dict,
    ) -> bool:
        """
        Send monitoring data to Kafka

        Args:
            agent_id: Agent identifier
            timestamp: Unix timestamp
            metrics: Metrics dictionary
            metadata: Metadata dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Construct monitoring data message
            monitoring_data = {
                "agent_id": agent_id,
                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                "metrics": metrics,
                "metadata": metadata,
            }

            # Serialize to JSON
            kafka_message = json.dumps(monitoring_data)

            # Produce to Kafka
            self.producer.produce(
                KafkaTopics.MONITORING_DATA,
                key=agent_id.encode("utf-8"),
                value=kafka_message.encode("utf-8"),
                callback=self._delivery_callback,
            )

            # Flush to ensure delivery
            self.producer.poll(0)
            self.producer.flush(timeout=5)

            return True

        except Exception as e:
            print(f"✗ Error sending to Kafka: {e}")
            return False

    def send_command_response(
        self,
        command_id: str,
        agent_id: str,
        success: bool,
        message: str,
        result: dict,
    ) -> bool:
        """
        Send command response to Kafka

        Args:
            command_id: Command identifier
            agent_id: Agent identifier
            success: Whether command succeeded
            message: Response message
            result: Result dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            response_data = {
                "command_id": command_id,
                "agent_id": agent_id,
                "success": success,
                "message": message,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }

            kafka_message = json.dumps(response_data)

            self.producer.produce(
                KafkaTopics.COMMAND_RESPONSES,
                key=command_id.encode("utf-8"),
                value=kafka_message.encode("utf-8"),
                callback=self._delivery_callback,
            )

            self.producer.poll(0)
            self.producer.flush(timeout=5)

            return True

        except Exception as e:
            print(f"✗ Error sending command response to Kafka: {e}")
            return False

    def send_agent_status(
        self,
        agent_id: str,
        hostname: str,
        status: str,
        uptime_seconds: int = 0,
        metrics_sent: int = 0,
        errors: int = 0,
    ) -> bool:
        """
        Send agent status to Kafka

        Args:
            agent_id: Agent identifier
            hostname: Hostname
            status: Agent status (running, stopped, error, initializing)
            uptime_seconds: Agent uptime
            metrics_sent: Number of metrics sent
            errors: Number of errors

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            status_data = {
                "agent_id": agent_id,
                "hostname": hostname,
                "status": status,
                "last_heartbeat": datetime.now().isoformat(),
                "uptime_seconds": uptime_seconds,
                "metrics_sent": metrics_sent,
                "errors": errors,
            }

            kafka_message = json.dumps(status_data)

            self.producer.produce(
                KafkaTopics.AGENT_STATUS,
                key=agent_id.encode("utf-8"),
                value=kafka_message.encode("utf-8"),
                callback=self._delivery_callback,
            )

            self.producer.poll(0)
            self.producer.flush(timeout=5)

            return True

        except Exception as e:
            print(f"✗ Error sending agent status to Kafka: {e}")
            return False

    def _delivery_callback(self, err, msg):
        """Callback for Kafka message delivery confirmation"""
        if err:
            print(f"  ✗ Kafka delivery failed: {err}")
        else:
            print(
                f"  → Delivered to {msg.topic()} [partition {msg.partition()}, offset {msg.offset()}]"
            )

    def close(self):
        """Close the producer"""
        self.producer.flush()
        print("✓ Kafka producer closed")

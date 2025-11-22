"""
Kafka message schemas and serialization helpers.
Defines the structure of messages sent through different Kafka topics.
"""

from typing import Dict, Any
import json
from datetime import datetime


# ============================================================================
# Kafka Topics
# ============================================================================


class KafkaTopics:
    """Kafka topics used in the monitoring system"""

    MONITORING_DATA = "monitoring-data"


# ============================================================================
# Message Schemas (JSON format for Kafka)
# ============================================================================

# Topic: monitoring-data
# Messages sent from gRPC server to Kafka containing monitoring metrics
MONITORING_DATA_SCHEMA = {
    "agent_id": "string",  # Unique agent identifier
    "timestamp": "string (ISO 8601)",  # Collection timestamp
    "metrics": {
        "cpu_percent": "float",  # CPU usage (0-100)
        "memory_percent": "float",  # Memory usage (0-100)
        "memory_used_mb": "float",  # Memory used in MB
        "memory_total_mb": "float",  # Total memory in MB
        "disk_read_mb": "float",  # Disk read rate in MB/s
        "disk_write_mb": "float",  # Disk write rate in MB/s
        "net_in_mb": "float",  # Network incoming rate in MB/s
        "net_out_mb": "float",  # Network outgoing rate in MB/s
    },
    "metadata": "dict",  # Additional metadata
}

# Command (sent via gRPC streaming to agents)
# Start/Stop commands for agents
COMMAND_SCHEMA = {
    "agent_id": "string",  # Target agent ID
    "type": "string",  # Command type: start or stop
}


# ============================================================================
# Serialization Helpers
# ============================================================================


def serialize_monitoring_data(data: Dict[str, Any]) -> str:
    """
    Serialize monitoring data to JSON string for Kafka.

    Args:
        data: Dictionary containing monitoring data

    Returns:
        JSON string
    """
    if isinstance(data.get("timestamp"), datetime):
        data["timestamp"] = data["timestamp"].isoformat()
    return json.dumps(data)


def deserialize_message(message_bytes: bytes) -> Dict[str, Any]:
    """
    Deserialize Kafka message from bytes to dictionary.

    Args:
        message_bytes: Raw message bytes from Kafka

    Returns:
        Dictionary containing message data
    """
    return json.loads(message_bytes.decode("utf-8"))


# ============================================================================
# Example Messages
# ============================================================================

EXAMPLE_MONITORING_DATA = {
    "agent_id": "agent-001",
    "timestamp": "2025-11-22T10:30:00Z",
    "metrics": {
        "cpu_percent": 45.2,
        "memory_percent": 62.5,
        "memory_used_mb": 5000.0,
        "memory_total_mb": 8000.0,
        "disk_read_mb": 12.5,
        "disk_write_mb": 8.3,
        "net_in_mb": 5.2,
        "net_out_mb": 3.1,
    },
    "metadata": {"os": "Linux", "version": "Ubuntu 22.04"},
}

EXAMPLE_COMMAND = {
    "agent_id": "agent-001",
    "type": "stop",
}

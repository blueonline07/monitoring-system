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
    COMMANDS = "commands"
    COMMAND_RESPONSES = "command-responses"
    AGENT_STATUS = "agent-status"


# ============================================================================
# Message Schemas (JSON format for Kafka)
# ============================================================================

# Topic: monitoring-data
# Messages sent from gRPC server to Kafka containing monitoring metrics
MONITORING_DATA_SCHEMA = {
    "agent_id": "string",  # Unique agent identifier
    "hostname": "string",  # Hostname of monitored machine
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
        "custom_metrics": "dict",  # Additional custom metrics
    },
    "metadata": "dict",  # Additional metadata
}

# Topic: commands
# Commands sent from analysis application to agents via gRPC server
COMMAND_SCHEMA = {
    "command_id": "string",  # Unique command identifier
    "command_type": "string",  # Type: update_config, start_collection, stop_collection, restart_agent, get_status, custom
    "target_agent_id": "string|null",  # Target agent (null = broadcast)
    "parameters": "dict",  # Command parameters
    "timestamp": "string (ISO 8601)",  # Command creation timestamp
    "timeout": "int",  # Timeout in seconds
}

# Topic: command-responses
# Responses from agents after executing commands
COMMAND_RESPONSE_SCHEMA = {
    "command_id": "string",  # ID of executed command
    "agent_id": "string",  # Agent that executed the command
    "success": "bool",  # Execution success status
    "message": "string",  # Response message or error
    "result": "dict",  # Execution result data
    "timestamp": "string (ISO 8601)",  # Response timestamp
}

# Topic: agent-status
# Agent status updates and heartbeats
AGENT_STATUS_SCHEMA = {
    "agent_id": "string",  # Agent identifier
    "hostname": "string",  # Hostname
    "status": "string",  # Status: running, stopped, error, initializing
    "last_heartbeat": "string (ISO 8601)",  # Last heartbeat timestamp
    "uptime_seconds": "int",  # Agent uptime
    "metrics_sent": "int",  # Number of metrics sent
    "errors": "int",  # Number of errors encountered
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


def serialize_command(command: Dict[str, Any]) -> str:
    """
    Serialize command to JSON string for Kafka.

    Args:
        command: Dictionary containing command data

    Returns:
        JSON string
    """
    if isinstance(command.get("timestamp"), datetime):
        command["timestamp"] = command["timestamp"].isoformat()
    return json.dumps(command)


def serialize_command_response(response: Dict[str, Any]) -> str:
    """
    Serialize command response to JSON string for Kafka.

    Args:
        response: Dictionary containing response data

    Returns:
        JSON string
    """
    if isinstance(response.get("timestamp"), datetime):
        response["timestamp"] = response["timestamp"].isoformat()
    return json.dumps(response)


def serialize_agent_status(status: Dict[str, Any]) -> str:
    """
    Serialize agent status to JSON string for Kafka.

    Args:
        status: Dictionary containing agent status data

    Returns:
        JSON string
    """
    if isinstance(status.get("last_heartbeat"), datetime):
        status["last_heartbeat"] = status["last_heartbeat"].isoformat()
    return json.dumps(status)


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
    "hostname": "web-server-01",
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
        "custom_metrics": {},
    },
    "metadata": {"os": "Linux", "version": "Ubuntu 22.04"},
}

EXAMPLE_COMMAND = {
    "command_id": "cmd-12345",
    "command_type": "get_status",
    "target_agent_id": "agent-001",
    "parameters": {},
    "timestamp": "2025-11-22T10:31:00Z",
    "timeout": 30,
}

EXAMPLE_COMMAND_RESPONSE = {
    "command_id": "cmd-12345",
    "agent_id": "agent-001",
    "success": True,
    "message": "Status retrieved successfully",
    "result": {"status": "running", "uptime": "3600"},
    "timestamp": "2025-11-22T10:31:05Z",
}

EXAMPLE_AGENT_STATUS = {
    "agent_id": "agent-001",
    "hostname": "web-server-01",
    "status": "running",
    "last_heartbeat": "2025-11-22T10:32:00Z",
    "uptime_seconds": 3600,
    "metrics_sent": 720,
    "errors": 0,
}

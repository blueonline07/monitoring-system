"""
Configuration - Kafka topics and system settings
"""


class KafkaTopics:
    """Kafka topics used in the monitoring system"""

    MONITORING_DATA = "monitoring-data"  # gRPC Server → Analysis App
    COMMANDS = "commands"  # Analysis App → gRPC Server → Agents
    COMMAND_RESPONSES = "command-responses"  # Agents → gRPC Server → Analysis App
    AGENT_STATUS = "agent-status"  # Agent heartbeat/status updates

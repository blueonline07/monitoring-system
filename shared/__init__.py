"""
Shared module - Contains common data models, schemas, and protocol definitions
"""

from .models import (
    SystemMetrics,
    MonitoringData,
    Command,
    CommandType,
    CommandResponse,
    AgentStatus,
    AgentInfo,
    KafkaTopics,
    KafkaMessage,
    PluginInterface,
    MetricType,
)

from .kafka_schemas import (
    KafkaTopics as KafkaTopicsClass,
    serialize_monitoring_data,
    serialize_command,
    serialize_command_response,
    serialize_agent_status,
    deserialize_message,
)

__all__ = [
    # Models
    "SystemMetrics",
    "MonitoringData",
    "Command",
    "CommandType",
    "CommandResponse",
    "AgentStatus",
    "AgentInfo",
    "KafkaTopics",
    "KafkaMessage",
    "PluginInterface",
    "MetricType",
    # Kafka Schemas
    "KafkaTopicsClass",
    "serialize_monitoring_data",
    "serialize_command",
    "serialize_command_response",
    "serialize_agent_status",
    "deserialize_message",
]


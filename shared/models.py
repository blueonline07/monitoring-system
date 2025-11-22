"""
Data models for the monitoring tool system.
Includes metrics, commands, and message structures.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Monitoring Data Models
# ============================================================================


class MetricType(str, Enum):
    """Types of metrics that can be collected"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK_READ = "disk read"
    DISK_WRITE = "disk write"
    NET_IN = "net in"
    NET_OUT = "net out"
    CUSTOM = "custom"


class SystemMetrics(BaseModel):
    """System metrics collected by monitor agents"""

    timestamp: datetime = Field(
        default_factory=datetime.now, description="Time when metrics were collected"
    )
    cpu_percent: Optional[float] = Field(
        default=None, description="CPU usage percentage (0-100)", ge=0, le=100
    )
    memory_percent: Optional[float] = Field(
        default=None, description="Memory usage percentage (0-100)", ge=0, le=100
    )
    memory_used_mb: Optional[float] = Field(
        default=None, description="Memory used in MB"
    )
    memory_total_mb: Optional[float] = Field(
        default=None, description="Total memory in MB"
    )
    disk_read_mb: Optional[float] = Field(
        default=None, description="Disk read rate in MB/s"
    )
    disk_write_mb: Optional[float] = Field(
        default=None, description="Disk write rate in MB/s"
    )
    net_in_mb: Optional[float] = Field(
        default=None, description="Network incoming rate in MB/s"
    )
    net_out_mb: Optional[float] = Field(
        default=None, description="Network outgoing rate in MB/s"
    )
    custom_metrics: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional custom metrics"
    )


class MonitoringData(BaseModel):
    """
    Complete monitoring data package from Monitor Agent to Analysis Application.

    Flow: Monitor Agent → gRPC Server → Kafka (monitoring-data topic) → Analysis App

    Note: Analysis App never receives data directly from agents.
    All data flows through Kafka for persistence and decoupling.
    """

    agent_id: str = Field(description="Unique identifier of the monitoring agent")
    hostname: str = Field(description="Hostname of the monitored machine")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Time when data was collected"
    )
    metrics: SystemMetrics = Field(description="System metrics data")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata (OS, version, etc.)"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Command Models
# ============================================================================


class CommandType(str, Enum):
    """Types of commands that can be sent to agents"""

    UPDATE_CONFIG = "update_config"
    START_COLLECTION = "start_collection"
    STOP_COLLECTION = "stop_collection"
    RESTART_AGENT = "restart_agent"
    GET_STATUS = "get_status"
    CUSTOM = "custom"


class Command(BaseModel):
    """
    Command sent from Analysis Application to Monitor Agents.

    Flow: Analysis App → Kafka (commands topic) → gRPC Server → Monitor Agent

    Note: Analysis App never communicates directly with agents.
    All communication goes through Kafka, with gRPC Server acting as broker.
    """

    command_id: str = Field(description="Unique identifier for the command")
    command_type: CommandType = Field(description="Type of command to execute")
    target_agent_id: Optional[str] = Field(
        default=None, description="Target agent ID (None means broadcast to all)"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Command parameters"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Time when command was created"
    )
    timeout: Optional[int] = Field(default=30, description="Command timeout in seconds")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CommandResponse(BaseModel):
    """
    Response from Monitor Agent after executing a command.

    Flow: Monitor Agent → gRPC Server → Kafka (command-responses topic) → Analysis App

    The Analysis App consumes this from Kafka to verify command execution.
    """

    command_id: str = Field(description="ID of the command being responded to")
    agent_id: str = Field(description="ID of the agent sending the response")
    success: bool = Field(description="Whether the command executed successfully")
    message: Optional[str] = Field(
        default=None, description="Response message or error description"
    )
    result: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Command execution result data"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Time when response was created"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Agent Status Models
# ============================================================================


class AgentStatus(str, Enum):
    """Status of monitor agent"""

    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"


class AgentInfo(BaseModel):
    """
    Information about a monitor agent.
    """

    agent_id: str
    hostname: str
    status: AgentStatus
    last_heartbeat: datetime
    uptime_seconds: int = Field(default=0, description="Agent uptime in seconds")
    metrics_sent: int = Field(
        default=0, description="Number of metrics sent since start"
    )
    errors: int = Field(default=0, description="Number of errors encountered")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Kafka Message Models
# ============================================================================


class KafkaTopics(str, Enum):
    """
    Kafka topics used in the system.

    Kafka is the central hub - all communication between Analysis App and
    Monitor Agents flows through these topics via the gRPC Server broker.
    """

    MONITORING_DATA = "monitoring-data"  # gRPC Server → Analysis App
    COMMANDS = "commands"  # Analysis App → gRPC Server
    COMMAND_RESPONSES = "command-responses"  # gRPC Server → Analysis App
    AGENT_STATUS = "agent-status"  # gRPC Server → Analysis App


class KafkaMessage(BaseModel):
    """
    Wrapper for messages sent through Kafka.
    """

    topic: str = Field(description="Kafka topic name")
    key: Optional[str] = Field(default=None, description="Message key for partitioning")
    payload: Dict[str, Any] = Field(description="Message payload (JSON serializable)")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Plugin Interface
# ============================================================================


class PluginInterface(BaseModel):
    """
    Base interface for plugins.
    Plugins can modify or filter monitoring data before transmission.
    """

    name: str = Field(description="Plugin name")
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Plugin configuration"
    )

    def process(self, data: MonitoringData) -> Optional[MonitoringData]:
        """
        Process monitoring data. Return None to prevent transmission.
        This is meant to be overridden by plugin implementations.
        """
        return data

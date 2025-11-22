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


class MonitoringData(BaseModel):
    """
    Complete monitoring data package from Monitor Agent to Analysis Application.

    Flow: Monitor Agent → gRPC Server → Kafka (monitoring-data topic) → Analysis App

    Note: Analysis App never receives data directly from agents.
    All data flows through Kafka for persistence and decoupling.
    """

    agent_id: str = Field(description="Unique identifier of the monitoring agent")
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
    """Command types for agent control"""

    START = "start"
    STOP = "stop"


class Command(BaseModel):
    """
    Command sent to Monitor Agents via gRPC streaming (start/stop only).

    Flow: Analysis App → gRPC Server → Agent (via bidirectional stream)
    
    Note: Configuration is managed separately, not via commands.
    """

    agent_id: str = Field(description="Target agent ID")
    type: CommandType = Field(description="Command type (start/stop)")



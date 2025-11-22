# Data Models Reference

Complete reference for all data structures used in the monitoring system.

## Overview

The system uses three data model layers:
1. **Python (Pydantic)** - For validation and Python code
2. **gRPC (Protobuf)** - For Agent ↔ Server communication
3. **Kafka (JSON)** - For Server ↔ Analysis App communication

---

## Python Models (`shared/models.py`)

### SystemMetrics

System metrics collected from monitored hosts.

```python
class SystemMetrics(BaseModel):
    timestamp: datetime                  # Collection timestamp
    cpu_percent: Optional[float]         # CPU usage (0-100%)
    memory_percent: Optional[float]      # Memory usage (0-100%)
    memory_used_mb: Optional[float]      # Memory used in MB
    memory_total_mb: Optional[float]     # Total memory in MB
    disk_read_mb: Optional[float]        # Disk read rate (MB/s)
    disk_write_mb: Optional[float]       # Disk write rate (MB/s)
    net_in_mb: Optional[float]           # Network in rate (MB/s)
    net_out_mb: Optional[float]          # Network out rate (MB/s)
    custom_metrics: Optional[Dict]       # Custom metrics
```

### MonitoringData

Complete monitoring data package.

```python
class MonitoringData(BaseModel):
    agent_id: str                        # Agent identifier
    hostname: str                        # Hostname
    timestamp: datetime                  # Timestamp
    metrics: SystemMetrics               # Metrics data
    metadata: Optional[Dict]             # Metadata (OS, etc.)
```

### Command

Commands sent to agents.

```python
class CommandType(Enum):
    UPDATE_CONFIG = "update_config"
    START_COLLECTION = "start_collection"
    STOP_COLLECTION = "stop_collection"
    RESTART_AGENT = "restart_agent"
    GET_STATUS = "get_status"
    CUSTOM = "custom"

class Command(BaseModel):
    command_id: str                      # Command ID
    command_type: CommandType            # Command type
    target_agent_id: Optional[str]       # Target agent
    parameters: Optional[Dict]           # Parameters
    timestamp: datetime                  # Timestamp
    timeout: Optional[int] = 30          # Timeout (seconds)
```

### CommandResponse

Agent response after command execution.

```python
class CommandResponse(BaseModel):
    command_id: str                      # Command ID
    agent_id: str                        # Agent ID
    success: bool                        # Success status
    message: Optional[str]               # Response message
    result: Optional[Dict]               # Result data
    timestamp: datetime                  # Timestamp
```

---

## gRPC Models (`shared/monitoring.proto`)

### Service Definition

```protobuf
service MonitoringService {
    // Bidirectional streaming for agent-server communication
    rpc StreamCommunication(stream AgentMessage) returns (stream ServerMessage);
    
    // Agent registration (called once at startup)
    rpc RegisterAgent(AgentRegistration) returns (Ack);
}
```

### AgentMessage (Agent → Server)

```protobuf
message AgentMessage {
    oneof message {
        MetricsData metrics_data = 1;
        CommandResponseMessage command_response = 2;
        AgentHeartbeat heartbeat = 3;
    }
}
```

### ServerMessage (Server → Agent)

```protobuf
message ServerMessage {
    oneof message {
        CommandMessage command = 1;
        Ack acknowledgment = 2;
    }
}
```

### MetricsData

```protobuf
message MetricsData {
    string agent_id = 1;
    string hostname = 2;
    int64 timestamp = 3;
    SystemMetrics metrics = 4;
    map<string, string> metadata = 5;
}
```

---

## Kafka Messages (`shared/kafka_schemas.py`)

### Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `monitoring-data` | Server → Analysis | Agent metrics |
| `commands` | Analysis → Server | Commands to agents |
| `command-responses` | Server → Analysis | Command results |
| `agent-status` | Server → Analysis | Agent heartbeats |

### monitoring-data (JSON)

```json
{
    "agent_id": "agent-001",
    "hostname": "web-server-01",
    "timestamp": "2025-11-22T10:30:00.123456",
    "metrics": {
        "cpu_percent": 45.23,
        "memory_percent": 67.89,
        "memory_used_mb": 5000.0,
        "memory_total_mb": 8000.0,
        "disk_read_mb": 12.5,
        "disk_write_mb": 8.3,
        "net_in_mb": 5.2,
        "net_out_mb": 3.1,
        "custom_metrics": {}
    },
    "metadata": {
        "os": "posix",
        "mode": "mock"
    }
}
```

### commands (JSON)

```json
{
    "command_id": "cmd-12345",
    "command_type": "get_status",
    "target_agent_id": "agent-001",
    "parameters": {},
    "timestamp": "2025-11-22T10:31:00Z",
    "timeout": 30
}
```

### command-responses (JSON)

```json
{
    "command_id": "cmd-12345",
    "agent_id": "agent-001",
    "success": true,
    "message": "Status retrieved successfully",
    "result": {
        "status": "running",
        "uptime": "3600"
    },
    "timestamp": "2025-11-22T10:31:05Z"
}
```

---

## Usage Examples

### Creating Monitoring Data

```python
from shared.models import MonitoringData, SystemMetrics
from datetime import datetime

metrics = SystemMetrics(
    timestamp=datetime.now(),
    cpu_percent=45.2,
    memory_percent=62.5,
    memory_used_mb=5000.0,
    memory_total_mb=8000.0
)

data = MonitoringData(
    agent_id="agent-001",
    hostname="server-01",
    timestamp=datetime.now(),
    metrics=metrics,
    metadata={"os": "Linux"}
)

# Convert to JSON
json_str = data.model_dump_json()
```

### Sending via gRPC

```python
from shared import monitoring_pb2

metrics_data = monitoring_pb2.MetricsData(
    agent_id="agent-001",
    hostname="server-01",
    timestamp=int(datetime.now().timestamp()),
    metrics=monitoring_pb2.SystemMetrics(
        cpu_percent=45.2,
        memory_percent=62.5,
        memory_used_mb=5000.0,
        memory_total_mb=8000.0
    ),
    metadata={"os": "Linux"}
)

agent_message = monitoring_pb2.AgentMessage(metrics_data=metrics_data)
```

### Consuming from Kafka

```python
from confluent_kafka import Consumer
import json

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'analysis-group',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['monitoring-data'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    
    data = json.loads(msg.value().decode('utf-8'))
    print(f"Agent: {data['agent_id']}")
    print(f"CPU: {data['metrics']['cpu_percent']}%")
```

---

## Field Descriptions

### Metrics Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `cpu_percent` | float | 0-100 | CPU usage percentage |
| `memory_percent` | float | 0-100 | Memory usage percentage |
| `memory_used_mb` | float | >0 | Memory used in megabytes |
| `memory_total_mb` | float | >0 | Total memory in megabytes |
| `disk_read_mb` | float | ≥0 | Disk read rate (MB/s) |
| `disk_write_mb` | float | ≥0 | Disk write rate (MB/s) |
| `net_in_mb` | float | ≥0 | Network incoming rate (MB/s) |
| `net_out_mb` | float | ≥0 | Network outgoing rate (MB/s) |

### Timestamps

All timestamps use ISO 8601 format in JSON:
- Format: `"2025-11-22T10:30:00.123456"`
- Timezone: UTC
- Protobuf: Unix timestamp (int64)

---

## Validation

### Pydantic Validation

Models automatically validate:
- Required fields are present
- Types are correct
- Values are in valid ranges (e.g., CPU 0-100%)
- Datetime serialization to ISO 8601

### gRPC Validation

Protocol buffers provide:
- Type safety
- Efficient binary serialization
- Backward compatibility
- Field presence detection

### Kafka Validation

JSON schemas provide:
- Human-readable format
- Easy debugging
- Language-agnostic
- Schema evolution

---

For more details, see:
- `shared/models.py` - Python implementations
- `shared/monitoring.proto` - gRPC definitions
- `shared/kafka_schemas.py` - Kafka schemas


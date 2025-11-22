# Final Data Model Structure

## Protobuf Messages (`monitoring.proto`)

### Service
```protobuf
service MonitoringService {
    rpc StreamMetrics(stream MetricsRequest) returns (stream Command);
}
```

### Messages

**SystemMetrics** - System performance metrics
```protobuf
message SystemMetrics {
    double cpu_percent = 1;
    double memory_percent = 2;
    double memory_used_mb = 3;
    double memory_total_mb = 4;
    double disk_read_mb = 5;
    double disk_write_mb = 6;
    double net_in_mb = 7;
    double net_out_mb = 8;
    map<string, string> custom_metrics = 9;
}
```

**MetricsRequest** - Metrics sent from agent
```protobuf
message MetricsRequest {
    string agent_id = 1;
    int64 timestamp = 2;
    SystemMetrics metrics = 3;
    map<string, string> metadata = 4;
}
```

**Command** - Start/Stop commands (NO config)
```protobuf
enum CommandType {
    START = 0;
    STOP = 1;
}

message Command {
    string agent_id = 1;
    CommandType type = 2;
}
```

## Python Models (`models.py`)

**MetricType** - Enum for metric types
```python
class MetricType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK_READ = "disk read"
    DISK_WRITE = "disk write"
    NET_IN = "net in"
    NET_OUT = "net out"
    CUSTOM = "custom"
```

**SystemMetrics** - System metrics data
```python
class SystemMetrics(BaseModel):
    timestamp: datetime
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    memory_used_mb: Optional[float]
    memory_total_mb: Optional[float]
    disk_read_mb: Optional[float]
    disk_write_mb: Optional[float]
    net_in_mb: Optional[float]
    net_out_mb: Optional[float]
    custom_metrics: Optional[Dict[str, Any]]
```

**MonitoringData** - Complete monitoring package (NO hostname)
```python
class MonitoringData(BaseModel):
    agent_id: str
    timestamp: datetime
    metrics: SystemMetrics
    metadata: Optional[Dict[str, Any]]
```

**Command** - Start/Stop commands only
```python
class CommandType(str, Enum):
    START = "start"
    STOP = "stop"

class Command(BaseModel):
    agent_id: str
    type: CommandType
```

## Kafka Topics

**monitoring-data** - Only topic for metrics
```json
{
  "agent_id": "agent-001",
  "timestamp": "2025-11-22T10:30:00Z",
  "metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    ...
  },
  "metadata": {}
}
```

## Key Points

1. **No Configuration** - All config logic moved to separate module
2. **No Hostname** - Removed from metrics data
3. **Commands Only** - Server sends START/STOP commands only
4. **Single Kafka Topic** - Only `monitoring-data`
5. **Bidirectional Streaming** - Agent ↔ Server via gRPC

## Data Flow

```
Agent → StreamMetrics(MetricsRequest) → Server → Kafka
Agent ← StreamMetrics(Command) ← Server
```

Commands: START or STOP agent
Configuration: Handled in separate config module

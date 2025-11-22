# Data Model Updates Summary

## Protobuf Changes (`shared/monitoring.proto`)

### Service Definition
**Before**:
```
rpc SendMetrics(MetricsRequest) returns (MetricsResponse);
rpc RegisterAgent(AgentRegistration) returns (Ack);
```

**After**:
```
rpc StreamMetrics(stream MetricsRequest) returns (stream Command);
```

### Message Types

**Removed**:
- ❌ `MetricsResponse`
- ❌ `CommandType` enum
- ❌ `CommandMessage` 
- ❌ `CommandResponseMessage`
- ❌ `AgentRegistration`
- ❌ `AgentHeartbeat`
- ❌ `Ack`

**Simplified Command**:
```protobuf
message Command {
    string agent_id = 1;
    optional int32 interval = 2;
    repeated string metrics = 3;
    repeated string plugins = 4;
}
```

**Kept**:
- ✅ `SystemMetrics`
- ✅ `MetricsRequest`
- ✅ `Command` (new simplified version)

## Python Models Changes (`shared/models.py`)

**Removed**:
- ❌ `CommandType` enum
- ❌ `CommandResponse` model
- ❌ `AgentStatus` enum
- ❌ `AgentInfo` model
- ❌ `KafkaTopics` enum
- ❌ `KafkaMessage` model
- ❌ `PluginInterface` model

**Simplified Command**:
```python
class Command(BaseModel):
    agent_id: str
    interval: Optional[int]
    metrics: Optional[list[str]]
    plugins: Optional[list[str]]
```

**Kept**:
- ✅ `MetricType` enum
- ✅ `SystemMetrics`
- ✅ `MonitoringData`
- ✅ `Command` (new simplified version)

## Kafka Schema Changes (`shared/kafka_schemas.py`)

**Topics**:
- Before: `MONITORING_DATA`, `COMMANDS`, `COMMAND_RESPONSES`, `AGENT_STATUS`
- After: `MONITORING_DATA` only

**Removed Schemas**:
- ❌ `AGENT_STATUS_SCHEMA`
- ❌ `serialize_agent_status()`
- ❌ `EXAMPLE_AGENT_STATUS`

**Updated**:
- ✅ `COMMAND_SCHEMA` → `CONFIG_UPDATE_SCHEMA` (simplified)

## Architecture Changes

### Communication Flow
**Before**: Unary + Polling
```
Agent → SendMetrics → Server
Agent ← ListenForCommands ← Server
```

**After**: Bidirectional Streaming
```
Agent ↔ StreamMetrics ↔ Server
(Continuous bidirectional stream)
```

### Command Structure
**Before**:
```json
{
  "command_id": "cmd-123",
  "command_type": "update_config",
  "target_agent_id": "agent-001",
  "parameters": {"interval": "10", "metrics": "cpu,memory"},
  "timestamp": "2025-11-22T10:00:00Z",
  "timeout": 30
}
```

**After**:
```json
{
  "agent_id": "agent-001",
  "interval": 10,
  "metrics": ["cpu", "memory"],
  "plugins": ["zero"]
}
```

## Key Improvements

1. **Simplified** - Removed unnecessary complexity
2. **Streaming** - Real-time bidirectional communication
3. **Type-safe** - Better protobuf structure with optional and repeated fields
4. **Focused** - Only one Kafka topic needed (monitoring-data)
5. **Clean** - No redundant agent status tracking


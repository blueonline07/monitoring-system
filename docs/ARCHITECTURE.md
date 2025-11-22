# Architecture Documentation

## Project Structure

```
lab_ds/
├── shared/                          # Shared data models and schemas
│   ├── __init__.py
│   ├── models.py                    # Pydantic data models
│   ├── kafka_schemas.py             # Kafka message schemas
│   ├── monitoring.proto             # gRPC protocol definition
│   ├── monitoring_pb2.py            # Generated protobuf messages
│   └── monitoring_pb2_grpc.py       # Generated gRPC stubs
│
├── agent/                           # Monitor Agent Module
│   ├── __init__.py
│   ├── agent.py                     # Agent implementation
│   └── plugins/                     # Data processing plugins
│       └── __init__.py
│
├── grpc_server/                     # gRPC Server Module
│   ├── __init__.py
│   ├── server.py                    # gRPC server implementation
│   └── kafka_producer.py            # Kafka producer service
│
├── analysis_app/                    # Analysis Application Module
│   ├── __init__.py
│   └── consumer.py                  # Kafka consumer implementation
│
├── run_agent.py                     # ⭐ Entry point for agent
├── run_server.py                    # ⭐ Entry point for gRPC server
├── run_analysis.py                  # ⭐ Entry point for analysis app
│
├── docker-compose.yml               # Kafka infrastructure
├── requirements.txt                 # Python dependencies
├── README.md                        # Data model documentation
├── USAGE_GUIDE.md                   # Usage instructions
└── ARCHITECTURE.md                  # This file
```

## Module Descriptions

### 1. Shared Module (`shared/`)

**Purpose**: Contains all shared code used by multiple modules

**Components**:
- `models.py` - Pydantic data models for validation and serialization
- `kafka_schemas.py` - Kafka topic definitions and message schemas
- `monitoring.proto` - Protocol buffer definitions for gRPC
- `monitoring_pb2.py` & `monitoring_pb2_grpc.py` - Auto-generated gRPC code

**Key Classes**:
- `SystemMetrics` - System metrics data structure
- `MonitoringData` - Complete monitoring data package
- `Command` - Command structure
- `CommandResponse` - Command execution response
- `AgentInfo` - Agent status information
- `KafkaTopics` - Kafka topic names

### 2. Agent Module (`agent/`)

**Purpose**: Collects system metrics and sends to gRPC server

**Components**:
- `agent.py` - Main agent implementation
- `plugins/` - Directory for data processing plugins

**Key Class**: `MonitorAgent`

**Features**:
- Supports both mock and real data modes
- Configurable collection interval
- Plugin system for data filtering/processing
- Automatic reconnection on errors
- Command-line interface for configuration

**Usage**:
```python
from agent import MonitorAgent

agent = MonitorAgent(
    agent_id="agent-001",
    grpc_server_address="localhost:50051",
    mode="mock"  # or "real"
)
agent.run(interval=5, iterations=10)
```

### 3. gRPC Server Module (`grpc_server/`)

**Purpose**: Acts as a broker between agents (gRPC) and Kafka

**Components**:
- `server.py` - gRPC service implementation
- `kafka_producer.py` - Kafka producer service for message forwarding

**Key Classes**:
- `MonitoringService` - gRPC service that receives agent data
- `KafkaProducerService` - Kafka producer wrapper

**Responsibilities**:
- Receive metrics from agents via gRPC
- Convert protobuf to JSON
- Forward data to Kafka topics
- Route commands from Kafka to agents
- Handle agent registration and heartbeats

**Data Flow**:
```
Agent (gRPC) → MonitoringService → KafkaProducerService → Kafka
```

### 4. Analysis App Module (`analysis_app/`)

**Purpose**: Consumes monitoring data from Kafka for analysis

**Components**:
- `consumer.py` - Kafka consumer implementation

**Key Class**: `AnalysisApp`

**Features**:
- Subscribes to Kafka topics
- Deserializes and processes monitoring data
- Extensible processing pipeline
- Real-time data display
- Ready for database integration

**Usage**:
```python
from analysis_app import AnalysisApp

app = AnalysisApp(
    bootstrap_servers="localhost:9092",
    group_id="analysis-app-group"
)
app.run()
```

## Communication Flows

### 1. Monitoring Data Flow

```
┌─────────────────┐
│  Monitor Agent  │  • Collects metrics (mock or real)
│                 │  • Applies plugins (optional)
│                 │  • Creates MetricsRequest (protobuf)
└────────┬────────┘
         │
         │ gRPC (protobuf)
         │
         ▼
┌─────────────────┐
│  gRPC Server    │  • Receives MetricsRequest
│  - server.py    │  • Converts protobuf → dict
│  - kafka_       │  • Serializes to JSON
│    producer.py  │  • Produces to Kafka
└────────┬────────┘
         │
         │ Kafka (JSON)
         │
         ▼
┌─────────────────┐
│ Kafka Cluster   │  • Stores in "monitoring-data" topic
│                 │  • Provides persistence
└────────┬────────┘
         │
         │ Kafka (JSON)
         │
         ▼
┌─────────────────┐
│ Analysis App    │  • Consumes from Kafka
│  - consumer.py  │  • Deserializes JSON
│                 │  • Processes/displays data
└─────────────────┘
```

### 2. Command Flow (Future Implementation)

```
Analysis App → Kafka → gRPC Server → Agent
Agent → gRPC Server → Kafka → Analysis App (response)
```

## Design Patterns

### 1. Separation of Concerns
- **Agent**: Data collection only
- **gRPC Server**: Protocol bridging only
- **Analysis App**: Data processing only
- **Shared**: Common definitions

### 2. Dependency Inversion
- All modules depend on shared interfaces (Protocol Buffers, Kafka schemas)
- No direct dependencies between agent and analysis app

### 3. Plugin Architecture
- Agent supports pluggable data processors
- Easy to extend without modifying core code

### 4. Configuration via CLI
- All modules support command-line arguments
- No hard-coded configuration values

## Running the System

### Quick Start

1. **Start Kafka**:
```bash
docker-compose up -d
```

2. **Start gRPC Server**:
```bash
python3 run_server.py
```

3. **Start Analysis App**:
```bash
python3 run_analysis.py
```

4. **Start Agent**:
```bash
python3 run_agent.py --mode mock --iterations 10
```

### With Custom Configuration

**gRPC Server**:
```bash
python3 run_server.py --port 50051 --kafka localhost:9092
```

**Agent**:
```bash
python3 run_agent.py \
    --agent-id agent-prod-01 \
    --server localhost:50051 \
    --mode real \
    --interval 10 \
    --iterations 0  # infinite
```

**Analysis App**:
```bash
python3 run_analysis.py \
    --kafka localhost:9092 \
    --group-id analysis-team-1
```

## Extending the System

### Adding a Plugin

1. Create `agent/plugins/my_plugin.py`:
```python
from shared import MonitoringData, PluginInterface
from typing import Optional

class MyPlugin(PluginInterface):
    def __init__(self):
        super().__init__(name="my_plugin")
    
    def process(self, data: MonitoringData) -> Optional[MonitoringData]:
        # Your logic here
        # Return None to skip sending
        # Return modified data to send
        return data
```

2. Use in agent:
```python
from agent.plugins.my_plugin import MyPlugin

agent = MonitorAgent(...)
agent.add_plugin(MyPlugin())  # TODO: Implement add_plugin method
```

### Adding Custom Analysis

1. Extend `AnalysisApp` in `analysis_app/consumer.py`:
```python
class CustomAnalysisApp(AnalysisApp):
    def process_metrics(self, data: dict):
        super().process_metrics(data)  # Display
        
        # Add custom logic
        self.store_in_database(data)
        self.check_thresholds(data)
        self.generate_alerts(data)
```

## Kafka Topics

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `monitoring-data` | gRPC Server | Analysis App | Agent metrics |
| `commands` | Analysis App | gRPC Server | Commands to agents |
| `command-responses` | gRPC Server | Analysis App | Command results |
| `agent-status` | gRPC Server | Analysis App | Agent heartbeats |

## Configuration Files

- `docker-compose.yml` - Kafka cluster setup
- `requirements.txt` - Python dependencies
- `shared/monitoring.proto` - gRPC protocol definition

## Development Guidelines

1. **Adding New Features**:
   - Put shared code in `shared/`
   - Keep modules independent
   - Use protocol buffers for gRPC
   - Use JSON for Kafka

2. **Testing**:
   - Test each module independently
   - Use mock mode for agent testing
   - Verify messages in Kafka UI (http://localhost:8080)

3. **Deployment**:
   - Each module can run on separate machines
   - Scale agents horizontally
   - Scale analysis apps with consumer groups

## Dependencies

- **Python 3.7+**
- **gRPC** - Agent ↔ Server communication
- **Kafka** - Message broker
- **Pydantic** - Data validation
- **psutil** - System metrics (for real mode)
- **Docker** - For running Kafka

## Benefits of This Architecture

1. ✅ **Modularity** - Clean separation of concerns
2. ✅ **Scalability** - Each component scales independently
3. ✅ **Maintainability** - Easy to update individual modules
4. ✅ **Extensibility** - Plugin system for custom logic
5. ✅ **Testability** - Each module can be tested in isolation
6. ✅ **Flexibility** - Kafka provides loose coupling
7. ✅ **Reliability** - Kafka provides persistence and replay

## Next Steps

- [ ] Implement command flow (Analysis App → Agent)
- [ ] Add plugin system to agent
- [ ] Add database integration to analysis app
- [ ] Add authentication/authorization
- [ ] Add monitoring dashboard
- [ ] Add alerting system
- [ ] Add configuration management (etcd)


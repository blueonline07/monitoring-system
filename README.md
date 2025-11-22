# Monitoring Tool - Distributed System Monitoring

A modular monitoring system with plugin architecture that collects metrics from multiple agents, forwards them through a gRPC server to Kafka, and enables real-time analysis. Configuration is managed dynamically via etcd.

## 🎯 Quick Start

### 1. Start Services (Kafka, Zookeeper, etcd)
```bash
docker compose up -d
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note**: If you encounter protobuf compatibility issues with etcd3, set this environment variable:
```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
# Add to ~/.zshrc or ~/.bashrc for persistence
```

### 3. Set Up etcd Configuration
```bash
# Set up configuration for an agent
python setup_etcd_config.py --agent-id agent-001 --interval 5
```

### 4. Run the System

```bash
# Terminal 1: Start gRPC Server
python3 run_server.py

# Terminal 2: Start Analysis App
python3 run_analysis.py get-metrics

# Terminal 3: Start Agent
python3 run_agent.py --agent-id agent-001 --etcd-host localhost --etcd-port 2379
```

## 🏗️ Architecture

```
┌─────────────────┐                ┌─────────────────┐                ┌─────────────────┐
│ Monitor Agent   │─── gRPC ─────►│  gRPC Server  │──── Kafka ────►│  Analysis App   │
│                 │   (Stream)     │  (Broker)      │                │                 │
│ • Collects data │                │ • Forwards data │                │ • Analyzes data │
│ • Plugin system │                │                 │                │ • Prints to stdout│
│ • etcd config   │                │                 │                │                 │
└─────────────────┘                └─────────────────┘                └─────────────────┘
         │
         ▼
┌─────────────────┐
│      etcd       │
│  Configuration  │
│  Management     │
└─────────────────┘
```

**Key Features**:
- **Plugin Architecture**: Extensible plugin system for data processing
- **Dynamic Configuration**: Real-time configuration updates via etcd
- **Unidirectional Streaming**: Agent sends metrics to server via gRPC

## 📦 Module Structure

```
lab_ds/
├── agent/                    # Monitoring agent module
│   ├── agent.py              # Main agent orchestrator
│   ├── collect.py            # Metric collection module
│   ├── grpc.py               # gRPC communication module
│   ├── etcd_config.py        # etcd configuration manager
│   ├── plugin_manager.py     # Plugin loading and management
│   └── plugins/              # Plugin implementations
│       ├── base.py           # Base plugin class
│       └── deduplication.py  # Example deduplication plugin
├── grpc_server/              # gRPC server + Kafka producer
│   ├── server.py             # gRPC server implementation
│   └── kafka_producer.py     # Kafka producer service
├── analysis_app/             # Kafka consumer + analysis
│   └── consumer.py           # Analysis application
├── shared/                   # Protocol definitions & config
│   ├── monitoring.proto      # gRPC protocol definition
│   ├── config.py             # Kafka topics configuration
│   └── monitoring_pb2*.py    # Generated protobuf files
├── setup_etcd_config.py      # Helper script for etcd config
├── run_agent.py              # ⭐ Run agent
├── run_server.py             # ⭐ Run server
└── run_analysis.py           # ⭐ Run analysis app
```

## 🚀 Usage

### Agent Options
```bash
python3 run_agent.py \
    --agent-id agent-001 \
    --server localhost:50051 \
    --etcd-host localhost \
    --etcd-port 2379 \
    --config-key /monitor/config/agent-001  # Optional, defaults to /monitor/config/<agent-id>
```

### Server Options
```bash
python3 run_server.py
# Or with custom settings (if supported):
# python3 run_server.py --port 50051 --kafka localhost:9092
```

### Analysis App Options
```bash
python3 run_analysis.py get-metrics \
    --kafka localhost:9092 \
    --group-id my-team \
    --timeout 10
```

### Setting up etcd Configuration
```bash
python setup_etcd_config.py \
    --agent-id agent-001 \
    --interval 5 \
    --metrics cpu memory "disk read" "disk write" "net in" "net out" \
    --plugins agent.plugins.deduplication.DeduplicationPlugin
```

## 🔌 Plugin Architecture

The agent supports a plugin architecture for extensible data processing. Plugins can:
- Filter metrics
- Transform data
- Drop duplicate data (deduplication plugin example)
- Add custom processing logic

### Creating a Plugin

1. Create a new plugin class in `agent/plugins/`:
```python
from agent.plugins.base import BasePlugin
from shared import monitoring_pb2

class MyPlugin(BasePlugin):
    def initialize(self, config=None):
        # Initialize plugin
        pass
    
    def run(self, metrics_request):
        # Process metrics_request
        # Return modified request or None to drop
        return metrics_request
    
    def finalize(self):
        # Cleanup
        pass
```

2. Add plugin to etcd configuration:
```json
{
    "interval": 5,
    "metrics": ["cpu", "memory"],
    "plugins": ["agent.plugins.my_plugin.MyPlugin"]
}
```

## ⚙️ Configuration

### etcd Configuration Format

Configuration is stored in etcd at `/monitor/config/<agent-id>`:

```json
{
    "interval": 5,
    "metrics": [
        "cpu",
        "memory",
        "disk read",
        "disk write",
        "net in",
        "net out"
    ],
    "plugins": [
        "agent.plugins.deduplication.DeduplicationPlugin"
    ]
}
```

### Dynamic Configuration Updates

Configuration changes in etcd are automatically detected and applied:
- **Interval**: Updated in real-time
- **Metrics**: Updated immediately
- **Plugins**: Reloaded dynamically

### Setting Configuration

```bash
# Using the setup script
python setup_etcd_config.py --agent-id agent-001 --interval 10

# Or directly with etcdctl (if etcd is running in Docker)
docker exec -it etcd etcdctl put /monitor/config/agent-001 '{"interval": 10, "metrics": ["cpu", "memory"], "plugins": []}'
```

## 📊 Data Models

### System Metrics
- CPU usage (%)
- Memory usage (%)
- Memory used/total (MB)
- Disk read/write (MB/s)
- Network in/out (MB/s)

### Kafka Topics
- `monitoring-data` - Agent metrics → Analysis app (via gRPC server)

## 🔧 Requirements

### System Requirements
- Python 3.7+
- Docker (for Kafka, Zookeeper, and etcd)
- psutil (for real metrics mode)

### Services
- **Kafka**: `localhost:9092`
- **Kafka UI**: `http://localhost:8080`
- **etcd**: `localhost:2379`

### Environment Variables
For protobuf compatibility with etcd3:
```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

## 🎓 Examples

### Basic Usage
```bash
# Terminal 1: Start gRPC Server
python3 run_server.py

# Terminal 2: Start Analysis App
python3 run_analysis.py get-metrics

# Terminal 3: Set up and start agent
python setup_etcd_config.py --agent-id agent-001
python3 run_agent.py --agent-id agent-001
```

### Multiple Agents
```bash
# Set up configurations
python setup_etcd_config.py --agent-id agent-001 --interval 5
python setup_etcd_config.py --agent-id agent-002 --interval 10
python setup_etcd_config.py --agent-id agent-003 --interval 15

# Run multiple agents
python3 run_agent.py --agent-id agent-001 &
python3 run_agent.py --agent-id agent-002 &
python3 run_agent.py --agent-id agent-003 &
```

### Dynamic Configuration Update
```bash
# Update configuration while agent is running
python setup_etcd_config.py --agent-id agent-001 --interval 10 --metrics cpu memory

# Agent will automatically detect and apply the change
```

### Custom Plugin Example
```bash
# Add custom plugin to configuration
python setup_etcd_config.py \
    --agent-id agent-001 \
    --plugins agent.plugins.deduplication.DeduplicationPlugin agent.plugins.my_plugin.MyPlugin
```

## 🔍 Monitoring

### View Kafka Messages
```bash
open http://localhost:8080
```

### Check etcd Configuration
```bash
# Using etcdctl (if etcd is in Docker)
docker exec -it etcd etcdctl get /monitor/config/agent-001

# Or watch for changes
docker exec -it etcd etcdctl watch /monitor/config/agent-001
```

### Agent Logs
The agent logs show:
- Configuration loading from etcd
- Plugin loading
- Configuration updates
- Metrics collection

## 🛠️ Development

### Generate gRPC Code
```bash
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. shared/monitoring.proto
```

### Project Structure
- **agent/**: Modular agent with collect, grpc, and plugins modules
- **grpc_server/**: gRPC server that forwards metrics to Kafka
- **analysis_app/**: Kafka consumer that displays metrics
- **shared/**: Protocol definitions and shared configuration

### Adding New Plugins
1. Create plugin class extending `BasePlugin`
2. Implement `initialize()`, `run()`, and `finalize()` methods
3. Add plugin path to etcd configuration
4. Plugin will be loaded automatically

## 🐛 Troubleshooting

### etcd Connection Issues
- Ensure etcd is running: `docker ps | grep etcd`
- Check etcd port: `localhost:2379`
- Verify network connectivity

### Protobuf Compatibility
If you see protobuf errors with etcd3:
```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

### Configuration Not Updating
- Verify etcd watch is active (check agent logs)
- Ensure configuration key matches agent-id
- Check etcd connection

---

# Monitoring Tool - Distributed System Monitoring

A modular monitoring system that collects metrics from multiple agents, forwards them through a gRPC server to Kafka, and enables real-time analysis.

## 🎯 Quick Start

### 1. Start Kafka
```bash
docker-compose up -d
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the System

```bash
# Terminal 1: Start gRPC Server
python3 run_server.py

# Terminal 2: Start Analysis App
python3 run_analysis.py

# Terminal 3: Start Agent
python3 run_agent.py --mode mock --iterations 10
```

## 🏗️ Architecture

```
┌─────────────────┐                ┌─────────────────┐                ┌─────────────────┐
│ Monitor Agent   │─── gRPC ──────►│  gRPC Server    │──── Kafka ────►│  Analysis App   │
│                 │◄── Stream ─────│  (Broker)       │◄─── Kafka ─────│                 │
│ • Collects data │                │ • Forwards data │                │ • Analyzes data │
│ • Mock/Real     │                │ • Routes cmds   │                │ • Stores data   │
└─────────────────┘                └─────────────────┘                └─────────────────┘
```

**Key Feature**: **Bidirectional streaming** between agent and server (no polling!)

## 📦 Module Structure

```
lab_ds/
├── shared/              # Common data models & protocols
├── agent/              # Monitor agent (collects metrics)
├── grpc_server/        # gRPC server + Kafka producer
├── analysis_app/       # Kafka consumer + analysis
├── run_agent.py        # ⭐ Run agent
├── run_server.py       # ⭐ Run server
└── run_analysis.py     # ⭐ Run analysis app
```

## 🚀 Usage

### Agent Options
```bash
python3 run_agent.py \
    --agent-id agent-001 \
    --mode mock \            # or 'real' for actual metrics
    --interval 5 \           # seconds between metrics
    --iterations 10          # 0 = infinite
```

### Server Options
```bash
python3 run_server.py \
    --port 50051 \
    --kafka localhost:9092
```

### Analysis App Options
```bash
python3 run_analysis.py \
    --kafka localhost:9092 \
    --group-id my-team
```

## 📊 Data Models

### System Metrics
- CPU usage (%)
- Memory usage (%)
- Disk I/O (MB/s)
- Network I/O (MB/s)
- Custom metrics

### Kafka Topics
- `monitoring-data` - Agent metrics → Analysis app
- `commands` - Analysis app → Agent commands
- `command-responses` - Agent → Analysis app responses
- `agent-status` - Agent heartbeats & status

## 🔧 Configuration

### Requirements
- Python 3.7+
- Docker (for Kafka)
- psutil (for real metrics mode)

### Kafka
Accessible at:
- Bootstrap server: `localhost:9092`
- Kafka UI: `http://localhost:8080`

## 📚 Documentation

- **[docs/DATA_MODELS.md](docs/DATA_MODELS.md)** - Complete data model reference
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture & design
- **[docs/STREAMING.md](docs/STREAMING.md)** - Bidirectional streaming details
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development guide

## ✨ Features

✅ **Bidirectional Streaming** - Real-time communication, no polling  
✅ **Modular Architecture** - Independent, scalable components  
✅ **Mock & Real Modes** - Easy testing without actual system metrics  
✅ **Kafka Integration** - Persistent storage & decoupling  
✅ **Plugin System** - Extensible data processing  
✅ **CLI Configuration** - No hard-coded values  

## 🎓 Examples

### Basic Usage
```bash
# Quick test with mock data
python3 run_server.py &
python3 run_analysis.py &
python3 run_agent.py --mode mock --iterations 5
```

### Production Usage
```bash
# Real metrics, continuous monitoring
python3 run_agent.py \
    --agent-id prod-web-01 \
    --mode real \
    --interval 10 \
    --iterations 0
```

### Multiple Agents
```bash
# Run multiple agents simultaneously
python3 run_agent.py --agent-id agent-001 &
python3 run_agent.py --agent-id agent-002 &
python3 run_agent.py --agent-id agent-003 &
```

## 🔍 Monitoring

View Kafka messages in real-time:
```bash
open http://localhost:8080
```

Check active agents:
```bash
# Server logs show connected agents
✓ Agent registered: agent-001 on hostname
✓ Forwarded metrics #1 from agent 'agent-001' to Kafka
```

## 🛠️ Development

### Generate gRPC Code
```bash
cd shared
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. monitoring.proto
sed -i '' 's/import monitoring_pb2/from . import monitoring_pb2/' monitoring_pb2_grpc.py
```

### Run Tests
```bash
# Start all components and verify data flow
./test_flow.sh  # TODO: Create test script
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License

## 🙏 Acknowledgments

Built with:
- gRPC - Efficient RPC framework
- Kafka - Distributed streaming platform
- Pydantic - Data validation
- Protocol Buffers - Data serialization

---

**Need help?** Check the [docs/](docs/) folder for detailed documentation.

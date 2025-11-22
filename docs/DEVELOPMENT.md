# Development Guide

Guide for developers working on the monitoring system.

## Setup

### Prerequisites

- Python 3.7+
- Docker & Docker Compose
- Virtual environment (recommended)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd lab_ds

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Kafka
docker-compose up -d
```

---

## Project Structure

```
lab_ds/
├── shared/                     # Shared components
│   ├── models.py              # Pydantic data models
│   ├── kafka_schemas.py       # Kafka message schemas
│   ├── monitoring.proto       # gRPC protocol definition
│   ├── monitoring_pb2.py      # Generated (don't edit)
│   └── monitoring_pb2_grpc.py # Generated (don't edit)
│
├── agent/                      # Agent module
│   ├── agent.py               # Agent implementation
│   └── plugins/               # Plugin directory
│
├── grpc_server/                # Server module
│   ├── server.py              # gRPC service
│   └── kafka_producer.py      # Kafka producer
│
├── analysis_app/               # Analysis module
│   └── consumer.py            # Kafka consumer
│
├── docs/                       # Documentation
├── run_agent.py               # Agent entry point
├── run_server.py              # Server entry point
└── run_analysis.py            # Analysis entry point
```

---

## Development Workflow

### 1. Modifying Protocol Buffers

When you modify `shared/monitoring.proto`:

```bash
cd shared
python3 -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    monitoring.proto

# Fix import (required for package structure)
sed -i '' 's/import monitoring_pb2/from . import monitoring_pb2/' monitoring_pb2_grpc.py
```

Or use the helper script:
```bash
./scripts/regenerate_proto.sh  # TODO: Create this script
```

### 2. Adding New Metrics

**Step 1**: Update `shared/models.py`
```python
class SystemMetrics(BaseModel):
    # ... existing fields ...
    new_metric: Optional[float] = Field(default=None, description="New metric")
```

**Step 2**: Update `shared/monitoring.proto`
```protobuf
message SystemMetrics {
    // ... existing fields ...
    double new_metric = 9;
}
```

**Step 3**: Regenerate protobuf files (see above)

**Step 4**: Update agent collection in `agent/agent.py`
```python
def _collect_real_metrics(self):
    # ... collect new metric ...
    new_metric = collect_new_metric()
    
    return monitoring_pb2.SystemMetrics(
        # ... existing metrics ...
        new_metric=new_metric
    )
```

### 3. Adding New Commands

**Step 1**: Update `CommandType` enum in `shared/models.py`
```python
class CommandType(str, Enum):
    # ... existing types ...
    NEW_COMMAND = "new_command"
```

**Step 2**: Update `shared/monitoring.proto`
```protobuf
enum CommandType {
    // ... existing types ...
    NEW_COMMAND = 6;
}
```

**Step 3**: Implement command handler in `agent/agent.py`
```python
def handle_server_messages(self, responses):
    for response in responses:
        if response.HasField("command"):
            command = response.command
            
            if command.command_type == monitoring_pb2.NEW_COMMAND:
                # Handle new command
                result = self.execute_new_command(command)
                # Send response
                ...
```

### 4. Creating Plugins

Create `agent/plugins/my_plugin.py`:

```python
from shared.models import MonitoringData, PluginInterface
from typing import Optional

class MyPlugin(PluginInterface):
    def __init__(self):
        super().__init__(name="my_plugin")
        self.config = {"threshold": 80}
    
    def process(self, data: MonitoringData) -> Optional[MonitoringData]:
        # Example: Skip data if CPU below threshold
        if data.metrics.cpu_percent < self.config["threshold"]:
            return None  # Don't send
        return data  # Send as-is
```

Register plugin (TODO: Implement plugin system):
```python
from agent.plugins.my_plugin import MyPlugin

agent = MonitorAgent(...)
agent.register_plugin(MyPlugin())
```

---

## Testing

### Unit Tests

```bash
# TODO: Add pytest configuration
pytest tests/
```

### Integration Tests

```bash
# Start all components
python3 run_server.py &
SERVER_PID=$!

python3 run_analysis.py &
ANALYSIS_PID=$!

# Run agent for 5 iterations
python3 run_agent.py --mode mock --iterations 5

# Cleanup
kill $SERVER_PID $ANALYSIS_PID
```

### Manual Testing

```bash
# Terminal 1: Server with debug output
python3 run_server.py --kafka localhost:9092

# Terminal 2: Analysis app
python3 run_analysis.py

# Terminal 3: Agent with mock data
python3 run_agent.py --mode mock --iterations 5 --interval 2

# Terminal 4: Check Kafka UI
open http://localhost:8080
```

---

## Debugging

### Enable Verbose Logging

```bash
# Set environment variable
export GRPC_VERBOSITY=debug
export GRPC_TRACE=all

python3 run_server.py
```

### Check Kafka Messages

```bash
# List topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Read messages
docker exec kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic monitoring-data \
    --from-beginning \
    --max-messages 10
```

### Monitor Active Connections

```bash
# Check gRPC connections
lsof -i :50051

# Check Kafka connections  
lsof -i :9092
```

### Debug gRPC Streaming

Add print statements in `grpc_server/server.py`:

```python
def StreamCommunication(self, request_iterator, context):
    print(f"[DEBUG] Stream started")
    for agent_message in request_iterator:
        print(f"[DEBUG] Received message type: {agent_message.WhichOneof('message')}")
        # ... rest of code
```

---

## Code Style

### Python

Follow PEP 8:
```bash
# Format code
black agent/ grpc_server/ analysis_app/ shared/

# Lint
flake8 agent/ grpc_server/ analysis_app/ shared/
```

### Imports

Order imports:
1. Standard library
2. Third-party libraries
3. Local modules

```python
import sys
import os
from typing import Optional

import grpc
from confluent_kafka import Producer

from shared import monitoring_pb2
```

### Documentation

Use docstrings:
```python
def collect_metrics(self) -> monitoring_pb2.SystemMetrics:
    """
    Collect system metrics using psutil.
    
    Returns:
        SystemMetrics protobuf message with collected data
        
    Raises:
        ImportError: If psutil is not installed
    """
```

---

## Common Tasks

### Add New Kafka Topic

**Step 1**: Update `shared/kafka_schemas.py`
```python
class KafkaTopics(str, Enum):
    # ... existing topics ...
    NEW_TOPIC = "new-topic"
```

**Step 2**: Add schema definition
```python
NEW_TOPIC_SCHEMA = {
    "field1": "type",
    "field2": "type"
}
```

**Step 3**: Add serialization helper
```python
def serialize_new_topic(data: dict) -> str:
    return json.dumps(data)
```

**Step 4**: Update docker-compose.yml if needed (for auto-creation)

### Scale Components

**Multiple Agents**:
```bash
# Each agent needs unique ID
python3 run_agent.py --agent-id agent-001 &
python3 run_agent.py --agent-id agent-002 &
python3 run_agent.py --agent-id agent-003 &
```

**Multiple Analysis Apps**:
```bash
# Same group = load balancing
python3 run_analysis.py --group-id team-a &
python3 run_analysis.py --group-id team-a &

# Different groups = broadcast
python3 run_analysis.py --group-id team-b &
```

---

## Performance Optimization

### Reduce Metrics Frequency

```bash
# Collect less frequently
python3 run_agent.py --interval 60  # Every minute
```

### Batch Metrics

Modify agent to buffer metrics:
```python
def generate_agent_messages(self, interval, iterations):
    buffer = []
    while self.running:
        metrics = self.collect_metrics()
        buffer.append(metrics)
        
        if len(buffer) >= 10:  # Send batch of 10
            for m in buffer:
                yield AgentMessage(metrics_data=m)
            buffer = []
```

### Compress Data

Enable gRPC compression:
```python
channel = grpc.insecure_channel(
    address,
    options=[('grpc.default_compression_algorithm', 1)]  # gzip
)
```

---

## Deployment

### Docker Images

Create Dockerfiles for each component:

**agent/Dockerfile**:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "run_agent.py"]
```

**Build and run**:
```bash
docker build -t monitor-agent -f agent/Dockerfile .
docker run monitor-agent --server grpc-server:50051
```

### Kubernetes

Create deployments for scalability:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitor-agent
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: agent
        image: monitor-agent:latest
        args: ["--server", "grpc-server:50051", "--mode", "real"]
```

---

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'shared'
```

**Solution**: Run from project root:
```bash
cd /path/to/lab_ds
python3 run_agent.py
```

### gRPC Connection Failed

```
grpc._channel._InactiveRpcError: StatusCode.UNAVAILABLE
```

**Solution**: Check server is running and address is correct

### Kafka Producer Timeout

```
KafkaError: _TIMED_OUT
```

**Solution**: Check Kafka is running:
```bash
docker ps | grep kafka
docker-compose restart kafka
```

---

## Resources

- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [Confluent Kafka Python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## Contributing

1. Create feature branch: `git checkout -b feature-name`
2. Make changes
3. Test locally
4. Submit pull request
5. Code review
6. Merge

---

For questions, see documentation or create an issue.


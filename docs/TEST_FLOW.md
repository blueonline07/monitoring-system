# Testing the Complete Flow: Mock Agent → gRPC → Kafka → Analysis App

This document shows how to test the complete data flow from the mock agent through gRPC server to Kafka.

## Architecture Flow

```
Mock Agent (mock_agent.py)
    │ Generates dummy metrics
    │ CPU, Memory, Disk, Network data
    ▼
gRPC Client
    │ Converts to protobuf
    │ Calls SendMetrics() RPC
    ▼
gRPC Server (grpc_server.py)
    │ Receives MetricsRequest
    │ Converts protobuf → JSON
    ▼
Kafka Producer
    │ Publishes to "monitoring-data" topic
    │ Key: agent_id
    ▼
Kafka Cluster (localhost:9092)
    │ Stores message persistently
    ▼
Analysis Consumer (analysis_consumer.py)
    │ Polls from "monitoring-data" topic
    │ Displays metrics
    ▼
✓ Data successfully transferred!
```

## Prerequisites

1. Kafka must be running:
```bash
docker-compose up -d
```

2. Verify Kafka is healthy:
```bash
# Check containers
docker ps

# You should see:
# - zookeeper
# - kafka
# - kafka-ui
```

3. Check Kafka UI (optional):
```
Open: http://localhost:8080
```

## Test Steps

### Step 1: Start the gRPC Server

In Terminal 1:
```bash
python3 grpc_server.py
```

You should see:
```
✓ Kafka producer initialized
============================================================
gRPC Server Started
============================================================
  Port: 50051
  Kafka topic: monitoring-data
  Waiting for agent connections...
============================================================
```

### Step 2: Start the Analysis Consumer

In Terminal 2:
```bash
python3 analysis_consumer.py
```

You should see:
```
✓ Subscribed to Kafka topic: monitoring-data
======================================================================
Analysis Application Started
======================================================================
Waiting for monitoring data from Kafka...
(Press Ctrl+C to stop)
======================================================================
```

### Step 3: Run the Mock Agent

In Terminal 3:
```bash
python3 mock_agent.py
```

You should see:
```
✓ Connected to gRPC server at localhost:50051
============================================================
Mock Agent Started: mock-agent-001
============================================================
  Hostname: your-hostname
  gRPC Server: localhost:50051
  Interval: 3s
  Iterations: 10
============================================================

[1] Sending mock metrics...
✓ Metrics sent successfully
  CPU: 45.23%
  Memory: 67.89%
  Response: Metrics received and pushed to Kafka successfully
```

### Expected Results

**In gRPC Server terminal:**
```
✓ Pushed metrics from agent 'mock-agent-001' to Kafka topic 'monitoring-data'
  → Message delivered to partition 0, offset 0
```

**In Analysis Consumer terminal:**
```
[Message #1]

======================================================================
📊 MONITORING DATA RECEIVED
======================================================================
  Agent ID:   mock-agent-001
  Hostname:   your-hostname
  Timestamp:  2025-11-22T10:30:00.123456
  OS Type:    Darwin

📈 System Metrics:
  CPU Usage:       45.23%
  Memory Usage:    67.89%
  Memory Used:     4523.45 / 8192.00 MB
  Disk Read:       23.45 MB/s
  Disk Write:      12.34 MB/s
  Network In:      5.67 MB/s
  Network Out:     3.21 MB/s
======================================================================
```

## Verification Checklist

- [x] Kafka is running (docker-compose up)
- [x] gRPC server started successfully
- [x] Analysis consumer subscribed to topic
- [x] Mock agent connects to gRPC server
- [x] Mock agent sends metrics successfully
- [x] gRPC server receives metrics via gRPC
- [x] gRPC server pushes to Kafka successfully
- [x] Analysis consumer receives data from Kafka
- [x] Data displayed correctly

## Troubleshooting

### Mock agent can't connect to gRPC server
```
✗ gRPC error: UNAVAILABLE - failed to connect to all addresses
```
**Solution**: Make sure gRPC server is running on port 50051

### gRPC server can't connect to Kafka
```
✗ Kafka delivery failed: ...
```
**Solution**: 
1. Check if Kafka is running: `docker ps`
2. Restart Kafka: `docker-compose restart kafka`
3. Check Kafka logs: `docker logs kafka`

### Consumer not receiving messages
**Solution**:
1. Check if topic exists: Visit http://localhost:8080
2. Check consumer group offset
3. Try resetting offset: Change `auto.offset.reset` to `earliest`

## Files Created

- `monitoring.proto` - Protocol buffer definition
- `monitoring_pb2.py` - Generated protobuf messages (auto-generated)
- `monitoring_pb2_grpc.py` - Generated gRPC stubs (auto-generated)
- `grpc_server.py` - gRPC server that forwards to Kafka
- `mock_agent.py` - Mock agent that sends test data
- `analysis_consumer.py` - Analysis app that consumes from Kafka

## Data Model Example

The data flowing through Kafka looks like this:

```json
{
  "agent_id": "mock-agent-001",
  "hostname": "your-hostname",
  "timestamp": "2025-11-22T10:30:00.123456",
  "metrics": {
    "cpu_percent": 45.23,
    "memory_percent": 67.89,
    "memory_used_mb": 4523.45,
    "memory_total_mb": 8192.0,
    "disk_read_mb": 23.45,
    "disk_write_mb": 12.34,
    "net_in_mb": 5.67,
    "net_out_mb": 3.21,
    "custom_metrics": {}
  },
  "metadata": {
    "os": "Darwin",
    "version": "24.6.0",
    "type": "mock"
  }
}
```

## Next Steps

1. ✅ Test with mock data (current setup)
2. Create real agent with psutil for actual system metrics
3. Implement command flow (Analysis App → Kafka → gRPC → Agent)
4. Add plugin system for data filtering
5. Add database storage in Analysis App
6. Add alerting based on thresholds


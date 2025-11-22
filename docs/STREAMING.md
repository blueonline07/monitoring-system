# Bidirectional Streaming Architecture

## Overview

The communication between gRPC Server and Monitor Agents uses **bidirectional streaming** instead of polling. This provides:

✅ **Real-time communication** - No polling delays  
✅ **Efficient resource usage** - Single persistent connection  
✅ **Instant command delivery** - Commands reach agents immediately  
✅ **Lower latency** - Continuous data flow without request/response overhead  

## Protocol Definition

### Service Definition

```protobuf
service MonitoringService {
    // Bidirectional streaming for agent-server communication
    rpc StreamCommunication(stream AgentMessage) returns (stream ServerMessage);
    
    // Agent registers itself with the server (called once at startup)
    rpc RegisterAgent(AgentRegistration) returns (Ack);
}
```

### Message Types

#### From Agent to Server (`AgentMessage`)

```protobuf
message AgentMessage {
    oneof message {
        MetricsData metrics_data = 1;        // System metrics
        CommandResponseMessage command_response = 2;  // Command execution result
        AgentHeartbeat heartbeat = 3;        // Heartbeat signal
    }
}
```

#### From Server to Agent (`ServerMessage`)

```protobuf
message ServerMessage {
    oneof message {
        CommandMessage command = 1;          // Command to execute
        Ack acknowledgment = 2;              // Acknowledgment of received data
    }
}
```

## Data Flow

### Agent → Server (Upstream)

```
┌─────────────────┐
│ Monitor Agent   │
└────────┬────────┘
         │
         │ Continuous Stream
         │
         ├─[1]─► MetricsData (every interval)
         │       - CPU, Memory, Disk, Network
         │       - Collected periodically
         │
         ├─[2]─► Heartbeat (with each metric)
         │       - Agent status: running
         │       - Keeps connection alive
         │
         └─[3]─► CommandResponse (when command completes)
                 - Result of executed command
                 - Success/failure status
```

### Server → Agent (Downstream)

```
┌─────────────────┐
│  gRPC Server    │
└────────┬────────┘
         │
         │ Continuous Stream
         │
         ├─[1]─► Acknowledgment (after each metric)
         │       - Confirms receipt
         │       - Success/failure status
         │
         └─[2]─► CommandMessage (from Kafka/Analysis App)
                 - Commands to execute
                 - Delivered instantly
```

## Implementation Details

### Agent Side (`agent/agent.py`)

**Key Features**:
- Generator function produces messages continuously
- Non-blocking queue for command responses
- Handles incoming server messages in main thread
- Graceful shutdown on completion or error

**Main Loop**:
```python
def generate_agent_messages(self, interval, iterations):
    while self.running:
        # Send heartbeat
        yield AgentMessage(heartbeat=...)
        
        # Collect and send metrics
        metrics = self.collect_metrics()
        yield AgentMessage(metrics_data=...)
        
        # Send any pending command responses
        while not self.message_queue.empty():
            response = self.message_queue.get()
            yield AgentMessage(command_response=response)
        
        time.sleep(interval)
```

**Streaming Call**:
```python
responses = self.stub.StreamCommunication(
    self.generate_agent_messages(interval, iterations)
)

# Handle server responses
for response in responses:
    if response.HasField("command"):
        # Execute command
    elif response.HasField("acknowledgment"):
        # Process acknowledgment
```

### Server Side (`grpc_server/server.py`)

**Key Features**:
- Handles multiple concurrent agent streams
- Tracks active agents with thread-safe dictionary
- Forwards metrics to Kafka immediately
- Can send commands back to agents instantly

**Main Handler**:
```python
def StreamCommunication(self, request_iterator, context):
    for agent_message in request_iterator:
        if agent_message.HasField("metrics_data"):
            # Forward to Kafka
            success = self.kafka_producer.send_monitoring_data(...)
            
            # Acknowledge back to agent
            yield ServerMessage(acknowledgment=...)
        
        elif agent_message.HasField("command_response"):
            # Forward response to Kafka
            self.kafka_producer.send_command_response(...)
            yield ServerMessage(acknowledgment=...)
        
        elif agent_message.HasField("heartbeat"):
            # Update agent status
            # Check for pending commands from Kafka
            # yield ServerMessage(command=...) if commands available
```

## Message Flow Example

### Scenario: Agent Sends Metrics and Receives Command

```
Agent                       gRPC Server                    Kafka
  │                              │                           │
  ├──[RegisterAgent]────────────►│                           │
  │◄──[Ack: registered]──────────┤                           │
  │                              │                           │
  ├──[StreamCommunication]───────►│                           │
  │      (start stream)           │                           │
  │                              │                           │
  ├──[Heartbeat]────────────────►│                           │
  │                              │                           │
  ├──[MetricsData]──────────────►│───[monitoring-data]──────►│
  │                              │                           │
  │◄─[Ack: metrics received]─────┤                           │
  │                              │                           │
  │                              │◄──[commands topic]────────│
  │                              │                           │
  │◄─[CommandMessage]────────────┤                           │
  │                              │                           │
  ├──[CommandResponse]──────────►│───[command-responses]────►│
  │                              │                           │
  │◄─[Ack: response received]────┤                           │
  │                              │                           │
  ├──[MetricsData]──────────────►│───[monitoring-data]──────►│
  │                              │                           │
  ⋮                              ⋮                           ⋮
```

## Advantages Over Polling

### Polling (Old Approach)
```
Agent: Send metrics → Wait for response → Sleep → Repeat
       └─ Each metric = 1 request + 1 response

Commands: Agent must poll server periodically to check
         └─ Adds latency and overhead
```

### Bidirectional Streaming (New Approach)
```
Agent: Open stream → Continuously send metrics + receive commands
       └─ Single connection, continuous flow

Commands: Delivered instantly when available
         └─ No polling delay
```

**Benefits**:
- 🚀 **Lower Latency** - No request/response overhead per metric
- 💰 **Less Overhead** - Single TCP connection vs many
- ⚡ **Instant Commands** - No polling delay
- 🔋 **Efficient** - Less CPU and network usage
- 🎯 **Scalable** - Server handles many concurrent streams

## Connection Management

### Agent Lifecycle

1. **Startup**:
   - Connect to gRPC server
   - Call `RegisterAgent()` (unary RPC)
   - Start bidirectional `StreamCommunication()`

2. **Running**:
   - Continuously send metrics via stream
   - Send heartbeats to keep connection alive
   - Receive and execute commands from stream
   - Send command responses via stream

3. **Shutdown**:
   - Complete current iteration
   - Close generator (stops sending)
   - Stream ends gracefully
   - Connection closed

### Server Behavior

- Accepts multiple concurrent agent streams
- Each agent stream runs independently
- Tracks active agents in memory
- Forwards all data to Kafka
- Can send commands from Kafka to agents

### Error Handling

**Connection Loss**:
- Agent: Detects stream error, can implement reconnection
- Server: Stream ends, marks agent as disconnected

**Network Issues**:
- gRPC handles automatic reconnection
- Heartbeats detect connection health

**Backpressure**:
- Agent generator respects flow control
- Server can pause processing if needed

## Configuration

Both agent and server now indicate streaming mode:

```bash
# Server
python3 run_server.py
# Output: "Mode: Bidirectional streaming (no polling)"

# Agent  
python3 run_agent.py --interval 5
# Output: "Using bidirectional streaming"
```

## Testing

### Test Streaming

```bash
# Terminal 1: Start server
python3 run_server.py

# Terminal 2: Start analysis app
python3 run_analysis.py

# Terminal 3: Start agent with streaming
python3 run_agent.py --mode mock --iterations 10 --interval 3
```

**Expected Behavior**:
- Agent sends 10 metrics continuously over stream
- Server acknowledges each metric
- Server forwards to Kafka immediately
- Analysis app receives all metrics
- Stream closes after 10 iterations

### Observe Stream

In server output, you should see:
```
✓ Agent registered: agent-001 on hostname
✓ Forwarded metrics #1 from agent 'agent-001' to Kafka
✓ Forwarded metrics #2 from agent 'agent-001' to Kafka
...
✓ Stream ended for agent 'agent-001' (10 metrics received)
```

In agent output, you should see:
```
✓ Agent registered: Agent registered successfully
[1] Streamed metrics:
  CPU: 45.23%
  Memory: 67.89%
[2] Streamed metrics:
...
✓ Completed 10 iterations. Stopping stream.
```

## Future Enhancements

- [ ] Implement command delivery from Kafka to agents
- [ ] Add stream reconnection logic
- [ ] Implement flow control for high-frequency metrics
- [ ] Add compression for metrics data
- [ ] Support multiple streams per agent (different metric types)
- [ ] Add authentication/authorization to streams

## Summary

The bidirectional streaming architecture provides a modern, efficient, and scalable solution for real-time monitoring. It eliminates polling overhead and enables instant command delivery while maintaining a clean separation of concerns between agent collection, server brokering, and Kafka persistence.


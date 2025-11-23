#!/bin/bash
# Terminal 1 - Start gRPC Server

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate

echo "=========================================="
echo "TERMINAL 1 - gRPC Server"
echo "=========================================="
echo "This server will:"
echo "  - Accept agent connections"
echo "  - Consume commands from Kafka"
echo "  - Route commands to connected agents"
echo "  - Forward metrics to Kafka"
echo ""
echo "Watch for these logs:"
echo "  ✓ gRPC Server running on port 50051"
echo "  ✓ Command consumer thread started"
echo "  [DEBUG] Agent connected: <agent-id>"
echo "  [DEBUG] Received command from Kafka"
echo "  [DEBUG] Queued command for agent"
echo "  [DEBUG] Sending command to agent"
echo "=========================================="
echo ""

python run_server.py

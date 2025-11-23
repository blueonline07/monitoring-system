#!/bin/bash
# Start Agent for Command Flow Testing

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

echo "=========================================="
echo "Starting Agent: test-cmd-agent"
echo "=========================================="
echo "Watch for:"
echo "  ✓ Connected to gRPC server"
echo "  ✓ Bidirectional stream established"
echo "  [DEBUG] Command receiver thread started"
echo "  [COMMAND] Received command: STATUS"
echo "=========================================="
echo ""

python run_agent.py --agent-id test-cmd-agent

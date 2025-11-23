#!/bin/bash
# Terminal 3 - Start Agent

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

echo "=========================================="
echo "TERMINAL 3 - Monitoring Agent"
echo "=========================================="
echo "This agent will:"
echo "  - Connect to gRPC server"
echo "  - Send metrics every 3 seconds"
echo "  - Receive and execute commands"
echo ""
echo "Watch for these logs:"
echo "  ✓ Agent test-cmd-agent initialized"
echo "  ✓ Connected to gRPC server"
echo "  ✓ Bidirectional stream established"
echo "  [DEBUG] Command receiver thread started"
echo "  [DEBUG] Sending metrics: cpu=X%, mem=Y%"
echo "  [COMMAND] Received command: <type>"
echo "  [COMMAND] Executing command: <type>"
echo "=========================================="
echo ""

python run_agent.py --agent-id test-cmd-agent

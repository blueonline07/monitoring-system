#!/bin/bash
# Terminal 2 - Analysis App (for sending commands and getting metrics)

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate

echo "=========================================="
echo "TERMINAL 2 - Analysis App (Command Sender)"
echo "=========================================="
echo ""
echo "Available commands:"
echo ""
echo "1. Send STATUS command:"
echo "   python run_analysis.py send-command test-cmd-agent STATUS"
echo ""
echo "2. Send STOP command (pause metrics):"
echo "   python run_analysis.py send-command test-cmd-agent STOP"
echo ""
echo "3. Send START command (resume metrics):"
echo "   python run_analysis.py send-command test-cmd-agent START"
echo ""
echo "4. Send UPDATE_CONFIG command:"
echo "   python run_analysis.py send-command test-cmd-agent UPDATE_CONFIG"
echo ""
echo "5. Send RESTART command:"
echo "   python run_analysis.py send-command test-cmd-agent RESTART"
echo ""
echo "6. Get metrics:"
echo "   python run_analysis.py get-metrics"
echo ""
echo "7. Monitor metrics continuously:"
echo "   python run_analysis.py monitor --duration 30"
echo ""
echo "8. Run automated test:"
echo "   python test_command_flow_simple.py"
echo ""
echo "=========================================="
echo ""
echo "Waiting for commands..."
echo "Type your command or press Ctrl+C to exit"
echo ""

# Keep terminal open
bash

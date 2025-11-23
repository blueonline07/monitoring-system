#!/bin/bash
# Quick test script for plugin system

echo "======================================"
echo "Plugin System Verification"
echo "======================================"
echo ""

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate

echo "[1/3] Running unit tests..."
python test_plugin.py
if [ $? -eq 0 ]; then
    echo "✅ Unit tests passed"
else
    echo "❌ Unit tests failed"
    exit 1
fi

echo ""
echo "[2/3] Running real-time metrics test..."
timeout 12 python test_plugin_realtime.py
if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "✅ Real-time test completed"
else
    echo "❌ Real-time test failed"
    exit 1
fi

echo ""
echo "[3/3] Checking plugin configuration..."
if grep -q "DeduplicationPlugin" agent/etcd_config.py; then
    echo "✅ Plugin enabled in config"
else
    echo "❌ Plugin not found in config"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ All Plugin Tests Passed!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Run the full system with 3 terminals"
echo "2. Check Terminal 3 for '[DeduplicationPlugin] initialized'"
echo "3. Look for 'Metrics dropped by plugin (duplicate)' messages"
echo ""
echo "See PLUGIN_TESTING_GUIDE.md for details"

#!/bin/bash
# Quick demonstration of all plugins

echo "=========================================="
echo "Advanced Plugin System Demo"
echo "=========================================="
echo ""

cd "/home/hung/Distributed System/lab/lab_ds"
source venv/bin/activate

echo "[1] Testing all plugins..."
python test_all_plugins.py

echo ""
echo "=========================================="
echo "✅ Plugin System Ready!"
echo "=========================================="
echo ""
echo "Available Plugins:"
echo "  1. DeduplicationPlugin   - Remove duplicates (30-70% reduction)"
echo "  2. ThresholdAlertPlugin  - Real-time alerts on high values"
echo "  3. AggregationPlugin     - Compress data (80% reduction)"
echo "  4. FilterPlugin          - Filter by conditions (40-60% reduction)"
echo ""
echo "Configuration Examples:"
echo ""
echo "# Traffic Reduction"
echo '"plugins": ["DeduplicationPlugin", "FilterPlugin"]'
echo ""
echo "# Real-Time Monitoring"
echo '"plugins": ["ThresholdAlertPlugin"]'
echo ""
echo "# Long-Term Storage"
echo '"plugins": ["AggregationPlugin"]'
echo '"window_size": 10'
echo ""
echo "Documentation: See ADVANCED_PLUGINS_GUIDE.md"
echo ""

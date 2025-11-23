"""
Comprehensive test for all plugins
"""
from agent.plugins.deduplication import DeduplicationPlugin
from agent.plugins.threshold_alert import ThresholdAlertPlugin
from agent.plugins.aggregation import AggregationPlugin
from agent.plugins.filter import FilterPlugin
from shared import monitoring_pb2
from datetime import datetime


def create_metrics_request(cpu=50.0, memory=60.0, disk_r=10.0, disk_w=5.0, 
                           net_in=2.0, net_out=1.0, agent_id="test-agent"):
    """Helper to create a MetricsRequest"""
    return monitoring_pb2.MetricsRequest(
        agent_id=agent_id,
        timestamp=int(datetime.now().timestamp()),
        metrics=monitoring_pb2.SystemMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            memory_used_mb=4096.0,
            memory_total_mb=8192.0,
            disk_read_mb=disk_r,
            disk_write_mb=disk_w,
            net_in_mb=net_in,
            net_out_mb=net_out,
        ),
        metadata={},
    )


def test_threshold_alert_plugin():
    """Test threshold alert plugin"""
    print("=" * 70)
    print("TEST 1: Threshold Alert Plugin")
    print("=" * 70)
    
    plugin = ThresholdAlertPlugin()
    plugin.initialize()
    
    print("\n[Test 1.1] Normal metrics (should pass, no alerts)")
    req1 = create_metrics_request(cpu=50.0, memory=60.0)
    result1 = plugin.run(req1)
    assert result1 is not None, "Should pass through"
    assert "alerts" not in result1.metadata, "Should have no alerts"
    print("  ✅ PASS - No alerts for normal metrics")
    
    print("\n[Test 1.2] High CPU (should pass with alert)")
    req2 = create_metrics_request(cpu=90.0, memory=60.0)
    result2 = plugin.run(req2)
    assert result2 is not None, "Should pass through"
    assert "alerts" in result2.metadata, "Should have alerts"
    print(f"  ✅ PASS - Alert generated: {result2.metadata['alerts']}")
    
    print("\n[Test 1.3] High memory (should pass with alert)")
    req3 = create_metrics_request(cpu=50.0, memory=90.0)
    result3 = plugin.run(req3)
    assert result3 is not None, "Should pass through"
    assert "alerts" in result3.metadata, "Should have alerts"
    print(f"  ✅ PASS - Alert generated: {result3.metadata['alerts']}")
    
    print("\n[Test 1.4] Multiple high metrics (should pass with multiple alerts)")
    req4 = create_metrics_request(cpu=95.0, memory=95.0)
    result4 = plugin.run(req4)
    assert result4 is not None, "Should pass through"
    assert "alerts" in result4.metadata, "Should have alerts"
    alert_count = int(result4.metadata.get("alert_count", "0"))
    assert alert_count >= 2, "Should have at least 2 alerts"
    print(f"  ✅ PASS - {alert_count} alerts generated")
    
    plugin.finalize()
    print("\n✅ Threshold Alert Plugin - ALL TESTS PASSED\n")
    return True


def test_aggregation_plugin():
    """Test aggregation plugin"""
    print("=" * 70)
    print("TEST 2: Aggregation Plugin")
    print("=" * 70)
    
    plugin = AggregationPlugin()
    plugin.initialize({"window_size": 3})
    
    print("\n[Test 2.1] First metric (should drop - collecting)")
    req1 = create_metrics_request(cpu=50.0, memory=60.0)
    result1 = plugin.run(req1)
    assert result1 is None, "Should drop (collecting)"
    print("  ✅ DROP - Collecting samples (1/3)")
    
    print("\n[Test 2.2] Second metric (should drop - collecting)")
    req2 = create_metrics_request(cpu=60.0, memory=65.0)
    result2 = plugin.run(req2)
    assert result2 is None, "Should drop (collecting)"
    print("  ✅ DROP - Collecting samples (2/3)")
    
    print("\n[Test 2.3] Third metric (should send aggregated)")
    req3 = create_metrics_request(cpu=70.0, memory=70.0)
    result3 = plugin.run(req3)
    assert result3 is not None, "Should send aggregated"
    assert "aggregation" in result3.metadata, "Should have aggregation metadata"
    # Average should be (50+60+70)/3 = 60
    assert 59.0 <= result3.metrics.cpu_percent <= 61.0, "CPU avg should be ~60"
    print(f"  ✅ SEND - Aggregated CPU: {result3.metrics.cpu_percent:.1f}% (avg of 50, 60, 70)")
    
    print("\n[Test 2.4] Fourth metric (should drop - new window)")
    req4 = create_metrics_request(cpu=80.0, memory=75.0)
    result4 = plugin.run(req4)
    assert result4 is None, "Should drop (new window)"
    print("  ✅ DROP - Collecting samples (1/3)")
    
    plugin.finalize()
    print("\n✅ Aggregation Plugin - ALL TESTS PASSED\n")
    return True


def test_filter_plugin():
    """Test filter plugin"""
    print("=" * 70)
    print("TEST 3: Filter Plugin")
    print("=" * 70)
    
    # Test 3.1: Filter by minimum CPU
    print("\n[Test 3.1] Filter by minimum CPU (30%)")
    plugin = FilterPlugin()
    plugin.initialize({"min_cpu": 30.0})
    
    req1 = create_metrics_request(cpu=20.0, memory=60.0)
    result1 = plugin.run(req1)
    assert result1 is None, "Should filter (CPU < 30%)"
    print("  ✅ FILTERED - CPU 20% < 30% threshold")
    
    req2 = create_metrics_request(cpu=40.0, memory=60.0)
    result2 = plugin.run(req2)
    assert result2 is not None, "Should pass (CPU >= 30%)"
    print("  ✅ PASS - CPU 40% >= 30% threshold")
    
    plugin.finalize()
    
    # Test 3.2: Filter idle systems
    print("\n[Test 3.2] Filter idle systems")
    plugin2 = FilterPlugin()
    plugin2.initialize({"send_idle": False})
    
    req3 = create_metrics_request(cpu=5.0, memory=60.0, disk_r=0.1, disk_w=0.1, 
                                  net_in=0.1, net_out=0.1)
    result3 = plugin2.run(req3)
    assert result3 is None, "Should filter (idle system)"
    print("  ✅ FILTERED - Idle system (low activity)")
    
    req4 = create_metrics_request(cpu=50.0, memory=60.0, disk_r=10.0, disk_w=5.0)
    result4 = plugin2.run(req4)
    assert result4 is not None, "Should pass (active system)"
    print("  ✅ PASS - Active system")
    
    plugin2.finalize()
    print("\n✅ Filter Plugin - ALL TESTS PASSED\n")
    return True


def test_plugin_chain():
    """Test chaining multiple plugins"""
    print("=" * 70)
    print("TEST 4: Plugin Chain (Dedup → Threshold → Filter)")
    print("=" * 70)
    
    # Create plugin chain
    dedup = DeduplicationPlugin()
    threshold = ThresholdAlertPlugin()
    filter_plugin = FilterPlugin()
    
    dedup.initialize()
    threshold.initialize({"thresholds": {"cpu_percent": 70.0}})
    filter_plugin.initialize({"min_cpu": 20.0})
    
    print("\n[Scenario 1] High CPU, first time")
    req1 = create_metrics_request(cpu=80.0, memory=60.0)
    r1 = dedup.run(req1)
    r1 = threshold.run(r1) if r1 else None
    r1 = filter_plugin.run(r1) if r1 else None
    assert r1 is not None, "Should pass all plugins"
    assert "alerts" in r1.metadata, "Should have alert"
    print("  ✅ PASS - Passed dedup, triggered alert, passed filter")
    
    print("\n[Scenario 2] Same metrics (duplicate)")
    req2 = create_metrics_request(cpu=80.0, memory=60.0)
    r2 = dedup.run(req2)
    assert r2 is None, "Should be dropped by dedup"
    print("  ⏭️  DROP - Dropped by deduplication")
    
    print("\n[Scenario 3] Low CPU (filtered)")
    req3 = create_metrics_request(cpu=10.0, memory=60.0)
    r3 = dedup.run(req3)
    r3 = threshold.run(r3) if r3 else None
    r3 = filter_plugin.run(r3) if r3 else None
    assert r3 is None, "Should be dropped by filter"
    print("  ⏭️  DROP - Passed dedup, no alert, dropped by filter")
    
    print("\n[Scenario 4] Normal metrics")
    req4 = create_metrics_request(cpu=50.0, memory=60.0)
    r4 = dedup.run(req4)
    r4 = threshold.run(r4) if r4 else None
    r4 = filter_plugin.run(r4) if r4 else None
    assert r4 is not None, "Should pass all plugins"
    assert "alerts" not in r4.metadata, "Should have no alerts"
    print("  ✅ PASS - Passed all plugins, no alerts")
    
    dedup.finalize()
    threshold.finalize()
    filter_plugin.finalize()
    
    print("\n✅ Plugin Chain - ALL TESTS PASSED\n")
    return True


def main():
    """Run all plugin tests"""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  COMPREHENSIVE PLUGIN TEST SUITE".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")
    
    results = []
    
    try:
        results.append(("Threshold Alert", test_threshold_alert_plugin()))
    except Exception as e:
        print(f"❌ Threshold Alert Plugin FAILED: {e}")
        results.append(("Threshold Alert", False))
    
    try:
        results.append(("Aggregation", test_aggregation_plugin()))
    except Exception as e:
        print(f"❌ Aggregation Plugin FAILED: {e}")
        results.append(("Aggregation", False))
    
    try:
        results.append(("Filter", test_filter_plugin()))
    except Exception as e:
        print(f"❌ Filter Plugin FAILED: {e}")
        results.append(("Filter", False))
    
    try:
        results.append(("Plugin Chain", test_plugin_chain()))
    except Exception as e:
        print(f"❌ Plugin Chain FAILED: {e}")
        results.append(("Plugin Chain", False))
    
    # Summary
    print("\n")
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name:20s}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL PLUGIN TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    print("\n")
    
    return all_passed


if __name__ == "__main__":
    main()

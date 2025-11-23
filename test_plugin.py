"""
Test script for deduplication plugin
"""
from agent.plugins.deduplication import DeduplicationPlugin
from shared import monitoring_pb2
from datetime import datetime


def create_metrics_request(cpu=50.0, memory=60.0, agent_id="test-agent"):
    """Helper to create a MetricsRequest"""
    return monitoring_pb2.MetricsRequest(
        agent_id=agent_id,
        timestamp=int(datetime.now().timestamp()),
        metrics=monitoring_pb2.SystemMetrics(
            cpu_percent=cpu,
            memory_percent=memory,
            memory_used_mb=4096.0,
            memory_total_mb=8192.0,
            disk_read_mb=10.0,
            disk_write_mb=5.0,
            net_in_mb=2.0,
            net_out_mb=1.0,
        ),
        metadata={},
    )


def test_deduplication_plugin():
    """Test deduplication plugin functionality"""
    print("=" * 70)
    print("Testing Deduplication Plugin")
    print("=" * 70)
    
    # Initialize plugin
    plugin = DeduplicationPlugin()
    plugin.initialize()
    
    # Test 1: First request should pass through
    print("\n[Test 1] First request (should PASS)")
    request1 = create_metrics_request(cpu=50.0, memory=60.0)
    result1 = plugin.run(request1)
    if result1 is not None:
        print("  ✅ PASS - First request allowed through")
    else:
        print("  ❌ FAIL - First request was dropped (should not happen)")
    
    # Test 2: Identical request should be dropped
    print("\n[Test 2] Identical request (should DROP)")
    request2 = create_metrics_request(cpu=50.0, memory=60.0)
    result2 = plugin.run(request2)
    if result2 is None:
        print("  ✅ DROP - Duplicate request was dropped (correct!)")
    else:
        print("  ❌ FAIL - Duplicate request was allowed (should be dropped)")
    
    # Test 3: Another identical request should also be dropped
    print("\n[Test 3] Another identical request (should DROP)")
    request3 = create_metrics_request(cpu=50.0, memory=60.0)
    result3 = plugin.run(request3)
    if result3 is None:
        print("  ✅ DROP - Duplicate request was dropped (correct!)")
    else:
        print("  ❌ FAIL - Duplicate request was allowed (should be dropped)")
    
    # Test 4: Different CPU value should pass through
    print("\n[Test 4] Different CPU value (should PASS)")
    request4 = create_metrics_request(cpu=75.0, memory=60.0)
    result4 = plugin.run(request4)
    if result4 is not None:
        print("  ✅ PASS - Different request allowed through")
    else:
        print("  ❌ FAIL - Different request was dropped (should pass)")
    
    # Test 5: Identical to previous (CPU=75) should be dropped
    print("\n[Test 5] Identical to previous (should DROP)")
    request5 = create_metrics_request(cpu=75.0, memory=60.0)
    result5 = plugin.run(request5)
    if result5 is None:
        print("  ✅ DROP - Duplicate request was dropped (correct!)")
    else:
        print("  ❌ FAIL - Duplicate request was allowed (should be dropped)")
    
    # Test 6: Different memory value should pass through
    print("\n[Test 6] Different memory value (should PASS)")
    request6 = create_metrics_request(cpu=75.0, memory=80.0)
    result6 = plugin.run(request6)
    if result6 is not None:
        print("  ✅ PASS - Different request allowed through")
    else:
        print("  ❌ FAIL - Different request was dropped (should pass)")
    
    # Finalize and show statistics
    print("\n" + "=" * 70)
    print("Statistics:")
    print("=" * 70)
    print(f"  Total sent:    {plugin.sent_count}")
    print(f"  Total dropped: {plugin.dropped_count}")
    print(f"  Expected sent: 3 (tests 1, 4, 6)")
    print(f"  Expected drop: 3 (tests 2, 3, 5)")
    
    plugin.finalize()
    
    # Verify results
    print("\n" + "=" * 70)
    success = (
        result1 is not None and  # Test 1: pass
        result2 is None and      # Test 2: drop
        result3 is None and      # Test 3: drop
        result4 is not None and  # Test 4: pass
        result5 is None and      # Test 5: drop
        result6 is not None and  # Test 6: pass
        plugin.sent_count == 3 and
        plugin.dropped_count == 3
    )
    
    if success:
        print("✅ ALL TESTS PASSED!")
        print("   - Plugin correctly drops duplicate metrics")
        print("   - Plugin correctly passes different metrics")
    else:
        print("❌ SOME TESTS FAILED")
        print("   - Check output above for details")
    
    print("=" * 70)
    
    return success


def test_plugin_sequence():
    """Test a realistic sequence of metrics"""
    print("\n\n" + "=" * 70)
    print("Realistic Sequence Test")
    print("=" * 70)
    print("Simulating agent sending metrics over time...")
    
    plugin = DeduplicationPlugin()
    plugin.initialize()
    
    # Simulate metrics sequence
    sequence = [
        (50.0, 60.0, "should PASS (first)"),
        (50.0, 60.0, "should DROP (dup)"),
        (50.0, 60.0, "should DROP (dup)"),
        (55.0, 60.0, "should PASS (CPU changed)"),
        (55.0, 60.0, "should DROP (dup)"),
        (55.0, 65.0, "should PASS (memory changed)"),
        (55.0, 65.0, "should DROP (dup)"),
        (50.0, 60.0, "should PASS (back to old values)"),
    ]
    
    passed = 0
    dropped = 0
    
    for i, (cpu, mem, expected) in enumerate(sequence, 1):
        request = create_metrics_request(cpu=cpu, memory=mem)
        result = plugin.run(request)
        
        status = "PASS" if result is not None else "DROP"
        symbol = "✅" if result is not None else "⏭️ "
        
        print(f"{symbol} [{i}] CPU={cpu:.1f}%, MEM={mem:.1f}% → {status} ({expected})")
        
        if result is not None:
            passed += 1
        else:
            dropped += 1
    
    print(f"\nResults: {passed} passed, {dropped} dropped")
    print(f"Expected: 4 passed, 4 dropped")
    
    plugin.finalize()
    
    success = (passed == 4 and dropped == 4)
    
    if success:
        print("\n✅ SEQUENCE TEST PASSED!")
    else:
        print("\n❌ SEQUENCE TEST FAILED!")
    
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    # Run both tests
    test1_pass = test_deduplication_plugin()
    test2_pass = test_plugin_sequence()
    
    print("\n\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Basic Test:    {'✅ PASSED' if test1_pass else '❌ FAILED'}")
    print(f"Sequence Test: {'✅ PASSED' if test2_pass else '❌ FAILED'}")
    
    if test1_pass and test2_pass:
        print("\n🎉 All plugin tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    print("=" * 70)

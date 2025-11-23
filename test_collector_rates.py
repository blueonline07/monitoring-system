"""
Test script to verify disk and network metrics are calculated as rates (MB/s)
"""
import time
from agent.collect import MetricCollector


def test_io_rates():
    """Test that disk and network I/O are reported as rates, not cumulative"""
    
    # Create collector with all metrics enabled
    collector = MetricCollector(
        agent_id="test-agent",
        active_metrics=["cpu", "memory", "disk_read", "disk_write", "net_in", "net_out"]
    )
    
    print("=" * 60)
    print("Testing I/O Rate Calculation")
    print("=" * 60)
    
    # First collection (will initialize previous values)
    print("\n[1] First collection (initializing)...")
    metrics1 = collector.collect_metrics()
    print(f"  Disk Read:  {metrics1['disk_read_mb']:.6f} MB/s")
    print(f"  Disk Write: {metrics1['disk_write_mb']:.6f} MB/s")
    print(f"  Net In:     {metrics1['net_in_mb']:.6f} MB/s")
    print(f"  Net Out:    {metrics1['net_out_mb']:.6f} MB/s")
    print("  ⚠️  First collection returns 0 (no previous data)")
    
    # Wait 2 seconds
    print("\n[2] Waiting 2 seconds...")
    time.sleep(2)
    
    # Second collection (should show rates)
    print("\n[3] Second collection (should show rates)...")
    metrics2 = collector.collect_metrics()
    print(f"  CPU:        {metrics2['cpu_percent']:.2f}%")
    print(f"  Memory:     {metrics2['memory_percent']:.2f}%")
    print(f"  Disk Read:  {metrics2['disk_read_mb']:.6f} MB/s")
    print(f"  Disk Write: {metrics2['disk_write_mb']:.6f} MB/s")
    print(f"  Net In:     {metrics2['net_in_mb']:.6f} MB/s")
    print(f"  Net Out:    {metrics2['net_out_mb']:.6f} MB/s")
    
    # Verify values are reasonable (should be small rates, not huge cumulative)
    print("\n" + "=" * 60)
    print("Validation:")
    print("=" * 60)
    
    checks = []
    
    # Disk rates should be < 1000 MB/s (reasonable for normal usage)
    if metrics2['disk_read_mb'] < 1000:
        checks.append("✅ Disk read is reasonable (< 1000 MB/s)")
    else:
        checks.append(f"❌ Disk read too high: {metrics2['disk_read_mb']:.2f} MB/s")
    
    if metrics2['disk_write_mb'] < 1000:
        checks.append("✅ Disk write is reasonable (< 1000 MB/s)")
    else:
        checks.append(f"❌ Disk write too high: {metrics2['disk_write_mb']:.2f} MB/s")
    
    # Network rates should be < 1000 MB/s (reasonable for normal usage)
    if metrics2['net_in_mb'] < 1000:
        checks.append("✅ Net in is reasonable (< 1000 MB/s)")
    else:
        checks.append(f"❌ Net in too high: {metrics2['net_in_mb']:.2f} MB/s")
    
    if metrics2['net_out_mb'] < 1000:
        checks.append("✅ Net out is reasonable (< 1000 MB/s)")
    else:
        checks.append(f"❌ Net out too high: {metrics2['net_out_mb']:.2f} MB/s")
    
    for check in checks:
        print(f"  {check}")
    
    # All checks should pass
    all_passed = all("✅" in check for check in checks)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED: Disk and network are rate-based!")
    else:
        print("❌ TESTS FAILED: Values are not rates")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    test_io_rates()

"""
Test script to demonstrate plugin deduplication with real metrics
This simulates an agent running and shows which metrics get dropped
"""
import time
from agent.collect import MetricCollector
from agent.plugins.deduplication import DeduplicationPlugin
from shared import monitoring_pb2


def test_plugin_with_real_metrics():
    """Test plugin with real psutil metrics"""
    print("=" * 70)
    print("Testing Plugin with Real Metrics")
    print("=" * 70)
    print("This test collects real system metrics and shows deduplication")
    print("=" * 70)
    
    # Create collector
    collector = MetricCollector(
        agent_id="plugin-test",
        active_metrics=["cpu", "memory", "disk_read", "disk_write", "net_in", "net_out"]
    )
    
    # Create plugin
    plugin = DeduplicationPlugin()
    plugin.initialize()
    
    print("\n[INFO] Collecting metrics every 1 second for 10 iterations...")
    print("[INFO] Plugin will drop duplicates automatically\n")
    
    sent_count = 0
    dropped_count = 0
    
    for i in range(10):
        # Collect real metrics
        metrics = collector.collect_metrics()
        metrics_request = collector.create_metrics_request(metrics)
        
        # Process through plugin
        result = plugin.run(metrics_request)
        
        # Display result
        if result is not None:
            sent_count += 1
            print(f"[{i+1:2d}] ✅ SENT - CPU:{metrics['cpu_percent']:5.1f}% MEM:{metrics['memory_percent']:5.1f}% "
                  f"DISK_R:{metrics['disk_read_mb']:6.3f} DISK_W:{metrics['disk_write_mb']:6.3f} "
                  f"NET_I:{metrics['net_in_mb']:6.3f} NET_O:{metrics['net_out_mb']:6.3f}")
        else:
            dropped_count += 1
            print(f"[{i+1:2d}] ⏭️  DROP - (duplicate)")
        
        time.sleep(1)
    
    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)
    print(f"  Sent:    {sent_count}")
    print(f"  Dropped: {dropped_count}")
    print(f"  Total:   {sent_count + dropped_count}")
    print("\n[INFO] If system is idle, many duplicates expected (network/disk = 0)")
    print("[INFO] If system is active, fewer duplicates (changing metrics)")
    
    plugin.finalize()
    
    print("=" * 70)


if __name__ == "__main__":
    test_plugin_with_real_metrics()

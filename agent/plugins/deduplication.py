"""
Deduplication Plugin - prevents sending identical data consecutively
"""
from typing import Dict, Any, Optional
from shared import monitoring_pb2
from agent.plugins.base import BasePlugin


class DeduplicationPlugin(BasePlugin):
    """Plugin that prevents sending data when it's identical to previously sent data"""
    
    def __init__(self):
        """Initialize deduplication plugin"""
        self.last_metrics = None
        self.dropped_count = 0
        self.sent_count = 0
    
    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """Initialize plugin with optional configuration"""
        self.last_metrics = None
        self.dropped_count = 0
        self.sent_count = 0
        print("[DeduplicationPlugin] initialized")
    
    def _metrics_to_dict(self, metrics: monitoring_pb2.SystemMetrics) -> Dict[str, float]:
        """Convert SystemMetrics to dictionary for comparison"""
        return {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "memory_total_mb": metrics.memory_total_mb,
            "disk_read_mb": metrics.disk_read_mb,
            "disk_write_mb": metrics.disk_write_mb,
            "net_in_mb": metrics.net_in_mb,
            "net_out_mb": metrics.net_out_mb,
        }
    
    def _are_metrics_equal(self, metrics1: Dict[str, float], metrics2: Dict[str, float]) -> bool:
        """Check if two metric dictionaries are equal"""
        return metrics1 == metrics2
    
    def run(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request - drop if identical to previous
        
        Args:
            metrics_request: The metrics request to process
            
        Returns:
            MetricsRequest if different from previous, None if identical
        """
        current_metrics = self._metrics_to_dict(metrics_request.metrics)
        
        if self.last_metrics is not None and self._are_metrics_equal(current_metrics, self.last_metrics):
            # Metrics are identical to previous, drop this request
            self.dropped_count += 1
            return None
        
        # Metrics are different, update last_metrics and allow through
        self.last_metrics = current_metrics
        self.sent_count += 1
        return metrics_request
    
    def finalize(self):
        """Finalize plugin and print statistics"""
        print(f"[DeduplicationPlugin] finalized - Sent: {self.sent_count}, Dropped: {self.dropped_count}")


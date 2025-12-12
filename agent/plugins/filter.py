"""
Filter Plugin - filters out metrics based on configurable conditions
"""

from typing import Dict, Any, Optional
from protobuf import monitoring_pb2
from agent.plugins.base import BasePlugin


class FilterPlugin(BasePlugin):
    """Plugin that filters metrics based on conditions"""

    def __init__(self):
        """Initialize filter plugin"""
        super().__init__()  # Initialize stats tracking
        self.min_cpu = 0.0  # Only send if CPU >= this value
        self.min_memory = 0.0  # Only send if memory >= this value
        self.send_idle = True  # Whether to send metrics when system is idle
        self.filtered_count = 0
        self.passed_count = 0

    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin with optional configuration

        Args:
            config: Configuration dict with filter conditions
                   - 'min_cpu': Minimum CPU % to send (default: 0)
                   - 'min_memory': Minimum memory % to send (default: 0)
                   - 'send_idle': Send when system idle (default: True)
        """
        if config:
            self.min_cpu = config.get("min_cpu", 0.0)
            self.min_memory = config.get("min_memory", 0.0)
            self.send_idle = config.get("send_idle", True)

        self.filtered_count = 0
        self.passed_count = 0

        print("[FilterPlugin] initialized")
        print(f"  min_cpu: {self.min_cpu}%")
        print(f"  min_memory: {self.min_memory}%")
        print(f"  send_idle: {self.send_idle}")

    def _is_idle(self, metrics: monitoring_pb2.SystemMetrics) -> bool:
        """
        Check if system is idle (low CPU and low disk/network activity)

        Args:
            metrics: SystemMetrics to check

        Returns:
            True if system is idle
        """
        return (
            metrics.cpu_percent < 10.0
            and metrics.disk_read_mb < 1.0
            and metrics.disk_write_mb < 1.0
            and metrics.net_in_mb < 1.0
            and metrics.net_out_mb < 1.0
        )

    def process(
        self, metrics_request: monitoring_pb2.MetricsRequest
    ) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request and filter based on conditions

        Args:
            metrics_request: The metrics request to process

        Returns:
            MetricsRequest if it passes filters, None if filtered out
        """
        metrics = metrics_request.metrics

        # Check if system is idle and we're not sending idle metrics
        if not self.send_idle and self._is_idle(metrics):
            self.filtered_count += 1
            print("[FilterPlugin] Filtered (idle system)")
            return None

        # Check CPU threshold
        if metrics.cpu_percent < self.min_cpu:
            self.filtered_count += 1
            print(
                f"[FilterPlugin] Filtered (CPU {metrics.cpu_percent:.1f}% < {self.min_cpu}%)"
            )
            return None

        # Check memory threshold
        if metrics.memory_percent < self.min_memory:
            self.filtered_count += 1
            print(
                f"[FilterPlugin] Filtered (Memory {metrics.memory_percent:.1f}% < {self.min_memory}%)"
            )
            return None

        # Passed all filters
        self.passed_count += 1
        return metrics_request

    def finalize(self):
        """Finalize plugin and print statistics"""
        total = self.passed_count + self.filtered_count
        filter_rate = (self.filtered_count / total * 100) if total > 0 else 0

        print("[FilterPlugin] finalized")
        print(f"  Total processed: {total}")
        print(f"  Passed: {self.passed_count}")
        print(f"  Filtered: {self.filtered_count}")
        print(f"  Filter rate: {filter_rate:.1f}%")

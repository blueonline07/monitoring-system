"""
Threshold Alert Plugin - alerts when metrics exceed configured thresholds
"""
from typing import Dict, Any, Optional
from shared import monitoring_pb2
from agent.plugins.base import BasePlugin


class ThresholdAlertPlugin(BasePlugin):
    """Plugin that generates alerts when metrics exceed thresholds"""

    def __init__(self):
        """Initialize threshold alert plugin"""
        super().__init__()  # Initialize stats tracking
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_read_mb": 100.0,  # MB/s
            "disk_write_mb": 100.0,  # MB/s
            "net_in_mb": 50.0,  # MB/s
            "net_out_mb": 50.0,  # MB/s
        }
        self.alert_count = 0
        self.check_count = 0
        self.alerts = []

    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin with optional configuration
        
        Args:
            config: Configuration dict that may contain 'thresholds' key
        """
        if config and "thresholds" in config:
            self.thresholds.update(config["thresholds"])

        self.alert_count = 0
        self.check_count = 0
        self.alerts = []
        print(f"[ThresholdAlertPlugin] initialized with thresholds: {self.thresholds}")

    def _check_threshold(self, metric_name: str, value: float) -> Optional[str]:
        """
        Check if a metric exceeds its threshold
        
        Args:
            metric_name: Name of the metric to check
            value: Current value of the metric
            
        Returns:
            Alert message if threshold exceeded, None otherwise
        """
        if metric_name in self.thresholds:
            threshold = self.thresholds[metric_name]
            if value > threshold:
                return f"⚠️  ALERT: {metric_name}={value:.2f} exceeds threshold {threshold:.2f}"
        return None

    def process(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request and check for threshold violations
        
        Args:
            metrics_request: The metrics request to process
            
        Returns:
            The same MetricsRequest (always passes through, adds alerts to metadata)
        """
        self.check_count += 1
        metrics = metrics_request.metrics

        # Check each metric against its threshold
        alerts_this_check = []

        checks = [
            ("cpu_percent", metrics.cpu_percent),
            ("memory_percent", metrics.memory_percent),
            ("disk_read_mb", metrics.disk_read_mb),
            ("disk_write_mb", metrics.disk_write_mb),
            ("net_in_mb", metrics.net_in_mb),
            ("net_out_mb", metrics.net_out_mb),
        ]

        for metric_name, value in checks:
            alert = self._check_threshold(metric_name, value)
            if alert:
                self.alert_count += 1
                alerts_this_check.append(alert)
                self.alerts.append(alert)
                print(alert)

        # Add alerts to metadata if any
        if alerts_this_check:
            metrics_request.metadata["alerts"] = "; ".join(alerts_this_check)
            metrics_request.metadata["alert_count"] = str(len(alerts_this_check))

        # Always pass through (non-blocking plugin)
        return metrics_request

    def finalize(self):
        """Finalize plugin and print statistics"""
        alert_rate = (self.alert_count / self.check_count * 100) if self.check_count > 0 else 0
        print(f"[ThresholdAlertPlugin] finalized")
        print(f"  Total checks: {self.check_count}")
        print(f"  Total alerts: {self.alert_count}")
        print(f"  Alert rate: {alert_rate:.1f}%")
        if self.alerts:
            print(f"  Recent alerts:")
            for alert in self.alerts[-5:]:  # Show last 5 alerts
                print(f"    {alert}")

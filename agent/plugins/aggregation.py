"""
Aggregation Plugin - aggregates metrics over time windows
"""

from typing import Dict, Any, Optional, List
from protobuf import monitoring_pb2
from agent.plugins.base import BasePlugin
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct


class AggregationPlugin(BasePlugin):
    """Plugin that aggregates metrics over a time window"""

    def __init__(self):
        """Initialize aggregation plugin"""
        super().__init__()  # Initialize stats tracking
        self.window_size = 5  # Number of samples to aggregate
        self.history: List[Dict[str, float]] = []
        self.aggregation_count = 0
        self.send_count = 0

    def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin with optional configuration

        Args:
            config: Configuration dict that may contain 'window_size' key
        """
        if config and "window_size" in config:
            self.window_size = config["window_size"]

        self.history = []
        self.aggregation_count = 0
        self.send_count = 0
        print(f"[AggregationPlugin] initialized with window_size={self.window_size}")

    def _aggregate_metrics(self, history: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate metrics from history (average, min, max)

        Args:
            history: List of metric dictionaries

        Returns:
            Aggregated metrics dictionary
        """
        if not history:
            return {}

        # Calculate averages
        metrics_keys = history[0].keys()
        aggregated = {}

        for key in metrics_keys:
            values = [h[key] for h in history]
            aggregated[f"{key}_avg"] = sum(values) / len(values)
            aggregated[f"{key}_min"] = min(values)
            aggregated[f"{key}_max"] = max(values)

        return aggregated

    def process(
        self, metrics_request: monitoring_pb2.MetricsRequest
    ) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request and aggregate over time window

        Args:
            metrics_request: The metrics request to process

        Returns:
            Aggregated MetricsRequest every window_size samples, None otherwise
        """
        metrics = metrics

        # Convert to dict
        current_metrics = {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "disk_read_mb": metrics.disk_read_mb,
            "disk_write_mb": metrics.disk_write_mb,
            "net_in_mb": metrics.net_in_mb,
            "net_out_mb": metrics.net_out_mb,
        }

        # Add to history
        self.history.append(current_metrics)

        # Always pass through, but add aggregation metadata when window is full
        # This ensures the stream never breaks while still providing aggregated insights

        # Check if window is full
        metadata = MessageToDict(metrics_request.metadata)
        if len(self.history) >= self.window_size:
            # Calculate aggregate statistics
            aggregated = self._aggregate_metrics(self.history)
            self.aggregation_count += 1
            self.send_count += 1

            # Mark this metric with aggregation data in metadata
            metadata["is_aggregated"] = "true"
            metadata["window_size"] = str(self.window_size)
            metadata["cpu_avg"] = f"{aggregated.get('cpu_percent_avg', 0):.1f}"
            metadata["cpu_min"] = f"{aggregated.get('cpu_percent_min', 0):.1f}"
            metadata["cpu_max"] = f"{aggregated.get('cpu_percent_max', 0):.1f}"
            metadata["mem_avg"] = f"{aggregated.get('memory_percent_avg', 0):.1f}"
            metadata["mem_min"] = f"{aggregated.get('memory_percent_min', 0):.1f}"
            metadata["mem_max"] = f"{aggregated.get('memory_percent_max', 0):.1f}"

            # Clear history for next window
            self.history = []

            print(
                f"[AggregationPlugin] ✓ Aggregated window completed (samples={self.send_count}, "
                + f"cpu_avg={aggregated.get('cpu_percent_avg', 0):.1f}%, "
                + f"mem_avg={aggregated.get('memory_percent_avg', 0):.1f}%)"
            )
        else:
            # Mark as raw (non-aggregated) data
            metadata["is_aggregated"] = "false"

        metrics_request.metadata = Struct()
        metrics_request.metadata.update(metadata)
        return metrics_request

    def finalize(self):
        """Finalize plugin and print statistics"""
        print("[AggregationPlugin] finalized")
        print(f"  Aggregations sent: {self.send_count}")
        print(f"  Samples per aggregation: {self.window_size}")
        print(
            f"  Total samples processed: {self.aggregation_count * self.window_size + len(self.history)}"
        )

"""
Aggregation Plugin - aggregates metrics over time windows
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from shared import monitoring_pb2
from agent.plugins.base import BasePlugin


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
    
    def process(self, metrics_request: monitoring_pb2.MetricsRequest) -> Optional[monitoring_pb2.MetricsRequest]:
        """
        Process metrics request and aggregate over time window
        
        Args:
            metrics_request: The metrics request to process
            
        Returns:
            Aggregated MetricsRequest every window_size samples, None otherwise
        """
        metrics = metrics_request.metrics
        
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
        
        # Check if window is full
        if len(self.history) >= self.window_size:
            # Aggregate metrics
            aggregated = self._aggregate_metrics(self.history)
            self.aggregation_count += 1
            self.send_count += 1
            
            # Create new metrics request with aggregated data
            aggregated_request = monitoring_pb2.MetricsRequest(
                agent_id=metrics_request.agent_id,
                timestamp=int(datetime.now().timestamp()),
                metrics=monitoring_pb2.SystemMetrics(
                    cpu_percent=aggregated.get("cpu_percent_avg", 0.0),
                    memory_percent=aggregated.get("memory_percent_avg", 0.0),
                    memory_used_mb=aggregated.get("memory_used_mb_avg", 0.0),
                    memory_total_mb=metrics.memory_total_mb,  # Keep original
                    disk_read_mb=aggregated.get("disk_read_mb_avg", 0.0),
                    disk_write_mb=aggregated.get("disk_write_mb_avg", 0.0),
                    net_in_mb=aggregated.get("net_in_mb_avg", 0.0),
                    net_out_mb=aggregated.get("net_out_mb_avg", 0.0),
                ),
            )
            
            # Add metadata
            aggregated_request.metadata["aggregation"] = f"window={self.window_size}"
            aggregated_request.metadata["count"] = str(len(self.history))
            aggregated_request.metadata["cpu_min"] = f"{aggregated.get('cpu_percent_min', 0):.2f}"
            aggregated_request.metadata["cpu_max"] = f"{aggregated.get('cpu_percent_max', 0):.2f}"
            aggregated_request.metadata["mem_min"] = f"{aggregated.get('memory_percent_min', 0):.2f}"
            aggregated_request.metadata["mem_max"] = f"{aggregated.get('memory_percent_max', 0):.2f}"
            
            # Clear history
            self.history = []
            
            print(f"[AggregationPlugin] Sending aggregated metrics (window={self.window_size})")
            return aggregated_request
        
        # Not ready to send yet
        return None
    
    def finalize(self):
        """Finalize plugin and print statistics"""
        print(f"[AggregationPlugin] finalized")
        print(f"  Aggregations sent: {self.send_count}")
        print(f"  Samples per aggregation: {self.window_size}")
        print(f"  Total samples processed: {self.aggregation_count * self.window_size + len(self.history)}")

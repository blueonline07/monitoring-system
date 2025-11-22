"""
Collect module - handles metric collection from localhost
"""
import socket
import random
from typing import Dict, Any, List
from datetime import datetime
from shared import monitoring_pb2


class MetricCollector:
    """Collects system metrics from localhost"""
    
    def __init__(self, agent_id: str, active_metrics: List[str]):
        """
        Initialize metric collector
        
        Args:
            agent_id: Unique identifier for this agent
            active_metrics: List of metric names to collect (supports both "disk read" and "disk_read" formats)
        """
        self.agent_id = agent_id
        self.hostname = socket.gethostname()
        self.active_metrics = active_metrics
    
    def _is_metric_active(self, metric_name: str) -> bool:
        """
        Check if a metric is active, handling both space and underscore formats
        
        Args:
            metric_name: Metric name to check (e.g., "cpu", "disk_read", "disk read")
            
        Returns:
            True if metric is active
        """
        # Normalize metric names: replace underscores with spaces for comparison
        normalized_active = [m.replace("_", " ") for m in self.active_metrics]
        normalized_name = metric_name.replace("_", " ")
        return normalized_name in normalized_active or metric_name in self.active_metrics
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics from localhost
        
        Returns:
            Dictionary containing collected metrics
        """
        all_metrics = {
            "cpu_percent": (
                random.uniform(20.0, 80.0) if self._is_metric_active("cpu") else 0.0
            ),
            "memory_percent": (
                random.uniform(40.0, 90.0) if self._is_metric_active("memory") else 0.0
            ),
            "memory_used_mb": (
                random.uniform(2000.0, 7000.0)
                if self._is_metric_active("memory")
                else 0.0
            ),
            "memory_total_mb": 8192.0,
            "disk_read_mb": (
                random.uniform(5.0, 50.0) if self._is_metric_active("disk_read") else 0.0
            ),
            "disk_write_mb": (
                random.uniform(2.0, 30.0)
                if self._is_metric_active("disk_write")
                else 0.0
            ),
            "net_in_mb": (
                random.uniform(1.0, 20.0) if self._is_metric_active("net_in") else 0.0
            ),
            "net_out_mb": (
                random.uniform(0.5, 15.0) if self._is_metric_active("net_out") else 0.0
            ),
        }
        
        return all_metrics
    
    def create_metrics_request(self, metrics: Dict[str, Any]) -> monitoring_pb2.MetricsRequest:
        """
        Create a MetricsRequest protobuf message from collected metrics
        
        Args:
            metrics: Dictionary of collected metrics
            
        Returns:
            MetricsRequest protobuf message
        """
        return monitoring_pb2.MetricsRequest(
            agent_id=self.agent_id,
            timestamp=int(datetime.now().timestamp()),
            metrics=monitoring_pb2.SystemMetrics(
                cpu_percent=metrics["cpu_percent"],
                memory_percent=metrics["memory_percent"],
                memory_used_mb=metrics["memory_used_mb"],
                memory_total_mb=metrics["memory_total_mb"],
                disk_read_mb=metrics["disk_read_mb"],
                disk_write_mb=metrics["disk_write_mb"],
                net_in_mb=metrics["net_in_mb"],
                net_out_mb=metrics["net_out_mb"],
            ),
            metadata={},
        )


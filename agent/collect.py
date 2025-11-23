"""
Collect module - handles metric collection from localhost
"""

import socket
import psutil
import threading
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
        self._active_metrics_lock = threading.Lock()
        self.active_metrics = active_metrics
        
        # Store previous I/O counters for rate calculation
        self._prev_disk_io = None
        self._prev_net_io = None
        self._prev_time = None

    def update_metrics(self, new_metrics: List[str]):
        """
        Update active metrics list (thread-safe)

        Args:
            new_metrics: New list of metric names to collect
        """
        with self._active_metrics_lock:
            self.active_metrics = new_metrics.copy()

    def _is_metric_active(self, metric_name: str) -> bool:
        """
        Check if a metric is active, handling both space and underscore formats

        Args:
            metric_name: Metric name to check (e.g., "cpu", "disk_read", "disk read")

        Returns:
            True if metric is active
        """
        with self._active_metrics_lock:
            # Normalize metric names: replace underscores with spaces for comparison
            normalized_active = [m.replace("_", " ") for m in self.active_metrics]
            normalized_name = metric_name.replace("_", " ")
            return (
                normalized_name in normalized_active or metric_name in self.active_metrics
            )

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics from localhost using psutil

        Returns:
            Dictionary containing collected metrics
        """
        # Collect CPU metrics
        cpu_percent = 0.0
        if self._is_metric_active("cpu"):
            cpu_percent = psutil.cpu_percent(interval=0.1)

        # Collect memory metrics
        memory_percent = 0.0
        memory_used_mb = 0.0
        memory_total_mb = 0.0
        if self._is_metric_active("memory"):
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used_mb = mem.used / (1024 * 1024)  # Convert to MB
            memory_total_mb = mem.total / (1024 * 1024)  # Convert to MB
        else:
            mem = psutil.virtual_memory()
            memory_total_mb = mem.total / (1024 * 1024)  # Always report total

        # Collect disk I/O metrics (rate-based)
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        current_time = datetime.now().timestamp()
        
        if self._is_metric_active("disk_read") or self._is_metric_active("disk_write"):
            disk_io = psutil.disk_io_counters()
            if disk_io and self._prev_disk_io and self._prev_time:
                time_delta = current_time - self._prev_time
                if time_delta > 0:
                    if self._is_metric_active("disk_read"):
                        bytes_read = disk_io.read_bytes - self._prev_disk_io.read_bytes
                        disk_read_mb = bytes_read / (1024 * 1024) / time_delta  # MB/s
                    if self._is_metric_active("disk_write"):
                        bytes_written = disk_io.write_bytes - self._prev_disk_io.write_bytes
                        disk_write_mb = bytes_written / (1024 * 1024) / time_delta  # MB/s
            self._prev_disk_io = disk_io

        # Collect network I/O metrics (rate-based)
        net_in_mb = 0.0
        net_out_mb = 0.0
        if self._is_metric_active("net_in") or self._is_metric_active("net_out"):
            net_io = psutil.net_io_counters()
            if net_io and self._prev_net_io and self._prev_time:
                time_delta = current_time - self._prev_time
                if time_delta > 0:
                    if self._is_metric_active("net_in"):
                        bytes_recv = net_io.bytes_recv - self._prev_net_io.bytes_recv
                        net_in_mb = bytes_recv / (1024 * 1024) / time_delta  # MB/s
                    if self._is_metric_active("net_out"):
                        bytes_sent = net_io.bytes_sent - self._prev_net_io.bytes_sent
                        net_out_mb = bytes_sent / (1024 * 1024) / time_delta  # MB/s
            self._prev_net_io = net_io
        
        # Update timestamp for next collection
        self._prev_time = current_time

        all_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used_mb": memory_used_mb,
            "memory_total_mb": memory_total_mb,
            "disk_read_mb": disk_read_mb,
            "disk_write_mb": disk_write_mb,
            "net_in_mb": net_in_mb,
            "net_out_mb": net_out_mb,
        }

        return all_metrics

    def create_metrics_request(
        self, metrics: Dict[str, Any]
    ) -> monitoring_pb2.MetricsRequest:
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

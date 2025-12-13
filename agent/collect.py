"""
Collect module - handles metric collection from localhost
"""

import threading
import time
from typing import Dict, Any, List
from datetime import datetime
from protobuf import monitoring_pb2
from google.protobuf.struct_pb2 import Struct

try:
    import psutil
except ImportError:
    raise ImportError(
        "psutil is required for metric collection. Install it with: pip install psutil"
    )


class MetricCollector:
    """Collects system metrics from localhost"""

    def __init__(self, hostname: str, active_metrics: List[str]):
        """
        Initialize metric collector

        Args:
            agent_id: Unique identifier for this agent
            active_metrics: List of metric names to collect (supports both "disk read" and "disk_read" formats)
        """
        self.hostname = hostname
        self._active_metrics_lock = threading.Lock()
        self.active_metrics = active_metrics
        self.flag = False
        self.key = ""
        # Initialize baseline measurements for rate-based metrics
        self._last_disk_io = psutil.disk_io_counters()
        self._last_net_io = psutil.net_io_counters()
        self._last_measurement_time = time.time()

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
                normalized_name in normalized_active
                or metric_name in self.active_metrics
            )

    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect system metrics from localhost

        Returns:
            Dictionary containing collected metrics
        """
        current_time = time.time()
        time_delta = current_time - self._last_measurement_time

        # Collect CPU metrics
        cpu_percent = 0.0
        if self._is_metric_active("cpu"):
            cpu_percent = psutil.cpu_percent(interval=0.1)

        # Collect memory metrics
        memory_percent = 0.0
        memory_used_mb = 0.0
        if self._is_metric_active("memory"):
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used_mb = mem.used / (1024 * 1024)  # Convert to MB

        memory_total_mb = psutil.virtual_memory().total / (1024 * 1024)

        # Collect disk I/O metrics (rate per second)
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        if self._is_metric_active("disk_read") or self._is_metric_active("disk_write"):
            try:
                current_disk_io = psutil.disk_io_counters()
                if current_disk_io and self._last_disk_io and time_delta > 0:
                    if self._is_metric_active("disk_read"):
                        read_bytes = (
                            current_disk_io.read_bytes - self._last_disk_io.read_bytes
                        )
                        disk_read_mb = (read_bytes / (1024 * 1024)) / time_delta

                    if self._is_metric_active("disk_write"):
                        write_bytes = (
                            current_disk_io.write_bytes - self._last_disk_io.write_bytes
                        )
                        disk_write_mb = (write_bytes / (1024 * 1024)) / time_delta

                    self._last_disk_io = current_disk_io
            except Exception as e:
                # Handle cases where disk_io_counters might not be available
                print(f"Error collecting disk metrics: {e}")

        # Collect network I/O metrics (rate per second)
        net_in_mb = 0.0
        net_out_mb = 0.0
        if self._is_metric_active("net_in") or self._is_metric_active("net_out"):
            try:
                current_net_io = psutil.net_io_counters()
                if current_net_io and self._last_net_io and time_delta > 0:
                    if self._is_metric_active("net_in"):
                        recv_bytes = (
                            current_net_io.bytes_recv - self._last_net_io.bytes_recv
                        )
                        net_in_mb = (recv_bytes / (1024 * 1024)) / time_delta

                    if self._is_metric_active("net_out"):
                        sent_bytes = (
                            current_net_io.bytes_sent - self._last_net_io.bytes_sent
                        )
                        net_out_mb = (sent_bytes / (1024 * 1024)) / time_delta

                    self._last_net_io = current_net_io
            except Exception as e:
                # Handle cases where net_io_counters might not be available
                print(f"Error collecting network metrics: {e}")

        self._last_measurement_time = current_time
        meta = {}
        if self.flag:
            procs = []

            for p in psutil.process_iter(["pid", "name"]):
                try:
                    cpu = p.cpu_percent(None)
                    mem = p.memory_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                procs.append(
                    {
                        "pid": p.pid,
                        "name": p.info["name"],
                        "cpu_percent": cpu,
                        "memory_percent": mem,
                    }
                )

            procs.sort(key=lambda x: x[self.key], reverse=True)
            meta = {"processes": procs[: min(5, len(procs))]}
            self.flag = False

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

        return all_metrics, meta

    def create_metrics_request(
        self, metrics: Dict[str, Any], metadata={}
    ) -> monitoring_pb2.MetricsRequest:
        """
        Create a MetricsRequest protobuf message from collected metrics

        Args:
            metrics: Dictionary of collected metrics

        Returns:
            MetricsRequest protobuf message
        """
        meta = Struct()
        meta.update(metadata)
        return monitoring_pb2.MetricsRequest(
            hostname=self.hostname,
            timestamp=int(datetime.now().timestamp()),
            metrics=monitoring_pb2.SystemMetrics(
                cpu_percent=98,
                memory_percent=metrics["memory_percent"],
                memory_used_mb=metrics["memory_used_mb"],
                memory_total_mb=metrics["memory_total_mb"],
                disk_read_mb=metrics["disk_read_mb"],
                disk_write_mb=metrics["disk_write_mb"],
                net_in_mb=metrics["net_in_mb"],
                net_out_mb=metrics["net_out_mb"],
            ),
            metadata=meta,
        )

    def run_diag(self, key):
        self.flag = True
        self.key = key

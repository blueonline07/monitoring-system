"""
Monitoring Agent - Modular architecture with collect, grpc, and plugins
"""

import time
import grpc
import threading
from typing import Dict, Any, Optional, Iterator
from protobuf import monitoring_pb2, monitoring_pb2_grpc
from google.protobuf.json_format import MessageToDict

from agent.collect import MetricCollector
from agent.plugin_manager import PluginManager
from agent.etcd_config import EtcdConfigManager


class MonitoringAgent:
    """Main monitoring agent with modular architecture"""

    def __init__(
        self,
        hostname: str,
        server_address: str,
        etcd_host: str = None,
        etcd_port: int = None,
        config_key: Optional[str] = None,
    ):
        """
        Initialize monitoring agent

        Args:
            hostname: Unique identifier for this agent
            server_address: Address of the gRPC server
            etcd_host: etcd server hostname (defaults to ETCD_HOST env var or localhost)
            etcd_port: etcd server port (defaults to ETCD_PORT env var or 2379)
            config_key: Optional custom config key (defaults to /monitor/config/<hostname>)
        """
        self.server_address = server_address
        self.hostname = hostname

        self.etcd_config = EtcdConfigManager(
            hostname=hostname,
            etcd_host=etcd_host,
            etcd_port=etcd_port,
            config_key=config_key,
        )
        initial_config = self.etcd_config.load_initial_config()
        self._interval_lock = threading.Lock()
        self._interval = initial_config.get("interval", 5)
        self.active_metrics = initial_config.get("metrics", [])
        self.collector = MetricCollector(hostname, self.active_metrics)
        self.channel = None
        self.stub = None
        self.connected = False
        self.plugin_manager = PluginManager(initial_config)
        self.running = False

    @property
    def interval(self) -> float:
        """Get current interval (thread-safe)"""
        with self._interval_lock:
            return self._interval

    def _update_interval(self, new_interval: float):
        """Update interval (thread-safe)"""
        with self._interval_lock:
            self._interval = new_interval

    def _on_config_update(self, new_config: Dict[str, Any]):
        """
        Handle configuration updates from etcd

        Args:
            new_config: New configuration dictionary
        """
        print(f"Applying config update for agent {self.hostname}...")

        new_interval = new_config.get("interval", 5)
        self._update_interval(new_interval)
        print(f"  Updated interval: {new_interval}s")

        new_metrics = new_config.get("metrics", [])
        if new_metrics != self.active_metrics:
            self.active_metrics = new_metrics
            self.collector.update_metrics(new_metrics)
            print(f"  Updated metrics: {new_metrics}")

        self.plugin_manager.load_plugins(new_config)
        print("Config update applied")

    def initialize(self):
        """Initialize agent and all modules"""
        print(f"Initializing agent {self.hostname}...")
        initial_config = self.etcd_config.get_config()
        self.plugin_manager.load_plugins(initial_config)
        self.etcd_config.start_watching()

        # Set up config update callback
        # Note: The etcd watch callback already updates the config manager's internal state
        # We'll check for config changes in the main loop or use a separate thread
        # For simplicity, we'll use a thread to monitor config changes
        def config_monitor():
            last_config = None
            while self.running:
                current_config = self.etcd_config.get_config()
                if last_config != current_config:
                    if last_config is not None:
                        self._on_config_update(current_config)
                    last_config = current_config.copy()
                time.sleep(1)

        self._config_monitor_thread = threading.Thread(
            target=config_monitor, daemon=True
        )

        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = monitoring_pb2_grpc.MonitoringStub(self.channel)
        self.connected = True

        self.running = True
        self._config_monitor_thread.start()
        print(f"Agent {self.hostname} initialized")

    def metrics_generator(self) -> Iterator[monitoring_pb2.MetricsRequest]:
        """
        Generator that yields metrics requests

        Yields:
            MetricsRequest messages
        """
        while self.running:
            metrics, metadata = self.collector.collect_metrics()
            self.etcd_config.save_heartbeat()
            metrics_request = self.collector.create_metrics_request(metrics, metadata)
            processed_request = self.plugin_manager.process_metrics(metrics_request)
            if processed_request is not None:
                yield processed_request
            time.sleep(self.interval)

    def run(self):
        """Run the agent - main execution loop"""
        try:
            response_stream = self.stub.StreamMetrics(self.metrics_generator())
            for cmd in response_stream:
                if cmd.type == monitoring_pb2.CommandType.CONFIG:
                    self.etcd_config.store_config(MessageToDict(cmd.params))
                elif cmd.type == monitoring_pb2.CommandType.DIAGNOSTIC:
                    self.collector.run_diag(key=MessageToDict(cmd.params)["key"])

        except KeyboardInterrupt:
            print("\nShutting down agent...")
        finally:
            self.finalize()

    def finalize(self):
        """Finalize agent and cleanup resources"""
        self.running = False
        self.etcd_config.stop_watching()
        self.plugin_manager.finalize_all()

        if self.channel:
            self.channel.close()
            self.connected = False

        self.etcd_config.close()

        print(f"Agent {self.hostname} finalized")

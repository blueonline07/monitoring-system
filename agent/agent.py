"""
Monitoring Agent - Modular architecture with collect, grpc, and plugins
"""

import time
import threading
import socket
from typing import Dict, Any, Optional, Iterator
from shared import monitoring_pb2, Config

from agent.collect import MetricCollector
from agent.grpc import GrpcClient
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
        # Initialize etcd config manager
        self.etcd_config = EtcdConfigManager(
            hostname=socket.gethostname(),
            etcd_host=Config.ETCD_HOST,
            etcd_port=Config.ETCD_PORT,
            config_key=config_key,
        )

        # Load initial configuration
        initial_config = self.etcd_config.load_initial_config()

        # Extract initial configuration
        self._interval_lock = threading.Lock()
        self._interval = initial_config.get("interval", 5)
        self.active_metrics = initial_config.get("metrics", [])

        # Initialize modules with initial config
        self.collector = MetricCollector(hostname, self.active_metrics)
        self.grpc_client = GrpcClient(server_address)
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
        print(f"🔄 Applying config update for agent {self.hostname}...")

        # Update interval
        new_interval = new_config.get("interval", 5)
        self._update_interval(new_interval)
        print(f"  Updated interval: {new_interval}s")

        # Update metrics
        new_metrics = new_config.get("metrics", [])
        if new_metrics != self.active_metrics:
            self.active_metrics = new_metrics
            self.collector.update_metrics(new_metrics)
            print(f"  Updated metrics: {new_metrics}")

        # Reload plugins
        self.plugin_manager.load_plugins(new_config)
        print(f"✓ Config update applied")

    def initialize(self):
        """Initialize agent and all modules"""
        print(f"Initializing agent {self.hostname}...")

        # Load plugins with initial config
        initial_config = self.etcd_config.get_config()
        self.plugin_manager.load_plugins(initial_config)

        # Start watching for config changes
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
                    if last_config is not None:  # Skip initial load
                        self._on_config_update(current_config)
                    last_config = current_config.copy()
                time.sleep(1)  # Check every second

        self._config_monitor_thread = threading.Thread(target=config_monitor, daemon=True)

        # Connect to gRPC server
        self.grpc_client.connect()

        self.running = True
        self._config_monitor_thread.start()
        print(f"✓ Agent {self.hostname} initialized")

    def metrics_generator(self) -> Iterator[monitoring_pb2.MetricsRequest]:
        """
        Generator that yields metrics requests

        Yields:
            MetricsRequest messages
        """
        while self.running:
            # Collect metrics
            metrics = self.collector.collect_metrics()
            metrics_request = self.collector.create_metrics_request(metrics)

            # Process through plugins
            processed_request = self.plugin_manager.process_metrics(metrics_request)

            # Only yield if not dropped by plugins
            if processed_request is not None:
                yield processed_request

            time.sleep(self.interval)

    def run(self):
        """Run the agent - main execution loop"""
        try:
            self.grpc_client.stream_metrics(metrics_generator=self.metrics_generator())
        except KeyboardInterrupt:
            print("\nShutting down agent...")
        finally:
            self.finalize()

    def finalize(self):
        """Finalize agent and cleanup resources"""
        self.running = False

        # Stop watching etcd config
        self.etcd_config.stop_watching()

        # Finalize plugins
        self.plugin_manager.finalize_all()

        # Disconnect from gRPC server
        self.grpc_client.disconnect()

        # Close etcd connection
        self.etcd_config.close()

        print(f"✓ Agent {self.hostname} finalized")

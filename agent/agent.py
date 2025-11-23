"""
Monitoring Agent - Modular architecture with bidirectional command support
"""

import os
import time
import threading
from typing import Dict, Any, Optional, Iterator
from shared import monitoring_pb2

from agent.collect import MetricCollector
from agent.grpc import GrpcClient
from agent.plugin_manager import PluginManager
from agent.etcd_config import EtcdConfigManager


class MonitoringAgent:
    """Main monitoring agent with bidirectional command support"""

    def __init__(
        self,
        agent_id: str,
        server_address: str,
        etcd_host: str = None,
        etcd_port: int = None,
        config_key: Optional[str] = None,
    ):
        """
        Initialize monitoring agent

        Args:
            agent_id: Unique identifier for this agent
            server_address: Address of the gRPC server
            etcd_host: etcd server hostname (defaults to ETCD_HOST env var or localhost)
            etcd_port: etcd server port (defaults to ETCD_PORT env var or 2379)
            config_key: Optional custom config key (defaults to /monitor/config/<agent_id>)
        """
        if etcd_host is None:
            etcd_host = os.getenv("ETCD_HOST", "localhost")
        if etcd_port is None:
            etcd_port = int(os.getenv("ETCD_PORT", "2379"))
        self.agent_id = agent_id
        self.server_address = server_address

        # Initialize etcd config manager
        self.etcd_config = EtcdConfigManager(
            agent_id=agent_id,
            etcd_host=etcd_host,
            etcd_port=etcd_port,
            config_key=config_key,
        )

        # Load initial configuration
        initial_config = self.etcd_config.load_initial_config()

        # Extract initial configuration
        self._interval_lock = threading.Lock()
        self._interval = initial_config.get("interval", 5)
        self.active_metrics = initial_config.get("metrics", [])

        # Initialize modules with initial config
        self.collector = MetricCollector(agent_id, self.active_metrics)
        self.grpc_client = GrpcClient(server_address)
        self.plugin_manager = PluginManager(initial_config)

        self.running = False
        self.collecting = True  # Control metrics collection (can be paused by STOP command)

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
        print(f"🔄 Applying config update for agent {self.agent_id}...")

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

    def _handle_command(self, command: monitoring_pb2.Command):
        """
        Handle incoming commands from server

        Args:
            command: Command protobuf message
        """
        print(f"[COMMAND] Received: agent_id={command.agent_id}, type={command.type}, params={dict(command.params)}")
        
        command_type = monitoring_pb2.CommandType.Name(command.type)
        
        if command_type == "START":
            print("[COMMAND] Executing START - resuming metrics collection")
            self.collecting = True
            
        elif command_type == "STOP":
            print("[COMMAND] Executing STOP - pausing metrics collection")
            self.collecting = False
            
        elif command_type == "UPDATE_CONFIG":
            print("[COMMAND] Executing UPDATE_CONFIG - reloading config from etcd")
            new_config = self.etcd_config.get_config()
            self._on_config_update(new_config)
            
        elif command_type == "RESTART":
            print("[COMMAND] Executing RESTART - restarting agent")
            # Could implement full restart logic here
            self.collecting = False
            time.sleep(1)
            self.collecting = True
            
        elif command_type == "STATUS":
            print(f"[COMMAND] Executing STATUS")
            print(f"  Agent ID: {self.agent_id}")
            print(f"  Running: {self.running}")
            print(f"  Collecting: {self.collecting}")
            print(f"  Interval: {self.interval}s")
            print(f"  Active metrics: {self.active_metrics}")
            
        else:
            print(f"[COMMAND] Unknown command type: {command_type}")

    def initialize(self):
        """Initialize agent and all modules"""
        print(f"Initializing agent {self.agent_id}...")

        # Load plugins with initial config
        initial_config = self.etcd_config.get_config()
        self.plugin_manager.load_plugins(initial_config)

        # Start watching for config changes
        self.etcd_config.start_watching()

        # Set up config update callback
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
        
        # Register command handler
        self.grpc_client.set_command_handler(self._handle_command)

        self.running = True
        self._config_monitor_thread.start()
        print(f"✓ Agent {self.agent_id} initialized")

    def metrics_generator(self) -> Iterator[monitoring_pb2.MetricsRequest]:
        """
        Generator that yields metrics requests

        Yields:
            MetricsRequest messages
        """
        while self.running:
            # Only collect and send if collecting is enabled
            if self.collecting:
                # Collect metrics
                metrics = self.collector.collect_metrics()
                metrics_request = self.collector.create_metrics_request(metrics)

                # Process through plugins
                processed_request = self.plugin_manager.process_metrics(metrics_request)

                # Only yield if not dropped by plugins
                if processed_request is not None:
                    print(f"[DEBUG] Sending metrics: cpu={metrics['cpu_percent']:.1f}%, mem={metrics['memory_percent']:.1f}%")
                    yield processed_request
                else:
                    print("[DEBUG] Metrics dropped by plugin (duplicate)")
            else:
                print("[DEBUG] Metrics collection paused (STOP command)")

            time.sleep(self.interval)

    def run(self):
        """Run the agent - main execution loop"""
        try:
            # Stream metrics to server (bidirectional)
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

        print(f"✓ Agent {self.agent_id} finalized")

"""
Monitoring Agent - Modular architecture with collect, grpc, and plugins
"""
import time
from typing import Dict, Any, Optional, Iterator
from shared import monitoring_pb2

from agent.collect import MetricCollector
from agent.grpc import GrpcClient
from agent.plugin_manager import PluginManager


class MonitoringAgent:
    """Main monitoring agent with modular architecture"""
    
    def __init__(self, agent_id: str, server_address: str, config: Dict[str, Any]):
        """
        Initialize monitoring agent
        
        Args:
            agent_id: Unique identifier for this agent
            server_address: Address of the gRPC server
            config: Configuration dictionary with interval, metrics, and plugins
        """
        self.agent_id = agent_id
        self.server_address = server_address
        self.config = config
        
        # Extract configuration
        self.interval = config.get("interval", 5)
        self.active_metrics = config.get("metrics", [])
        
        # Initialize modules
        self.collector = MetricCollector(agent_id, self.active_metrics)
        self.grpc_client = GrpcClient(server_address)
        self.plugin_manager = PluginManager(config)
        
        self.running = False
    
    def initialize(self):
        """Initialize agent and all modules"""
        print(f"Initializing agent {self.agent_id}...")
        
        # Load plugins
        self.plugin_manager.load_plugins()
        
        # Connect to gRPC server
        self.grpc_client.connect()
        
        self.running = True
        print(f"✓ Agent {self.agent_id} initialized")
    
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
            # Stream metrics to server
            self.grpc_client.stream_metrics(
                metrics_generator=self.metrics_generator()
            )
        except KeyboardInterrupt:
            print("\nShutting down agent...")
        finally:
            self.finalize()
    
    def finalize(self):
        """Finalize agent and cleanup resources"""
        self.running = False
        
        # Finalize plugins
        self.plugin_manager.finalize_all()
        
        # Disconnect from gRPC server
        self.grpc_client.disconnect()
        
        print(f"✓ Agent {self.agent_id} finalized")


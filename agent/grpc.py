"""
gRPC module - handles bidirectional communication with the centralized server
"""

import grpc
import threading
from typing import Iterator, Callable, Optional
from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


class GrpcClient:
    """Handles bidirectional gRPC communication with the monitoring server"""

    def __init__(self, server_address: str):
        """
        Initialize gRPC client

        Args:
            server_address: Address of the gRPC server (host:port)
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self.connected = False
        self.command_handler: Optional[Callable] = None

    def connect(self):
        """Establish connection to gRPC server"""
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = monitoring_pb2_grpc.MonitoringServiceStub(self.channel)
        self.connected = True
        print(f"✓ Connected to gRPC server at {self.server_address}")

    def disconnect(self):
        """Close connection to gRPC server"""
        if self.channel:
            self.channel.close()
            self.connected = False
            print("✓ Disconnected from gRPC server")

    def set_command_handler(self, handler: Callable[[monitoring_pb2.Command], None]):
        """
        Set the command handler function

        Args:
            handler: Function to handle incoming commands
        """
        self.command_handler = handler
        print("[DEBUG] Command handler registered")

    def stream_metrics(
        self, metrics_generator: Iterator[monitoring_pb2.MetricsRequest]
    ):
        """
        Bidirectional streaming: Send metrics AND receive commands

        Args:
            metrics_generator: Generator that yields MetricsRequest messages
        """
        if not self.connected:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")

        try:
            print("[DEBUG] Starting bidirectional stream...")
            
            # Bidirectional streaming: send metrics, receive commands
            response_iterator = self.stub.StreamMetrics(metrics_generator)
            
            print("[DEBUG] Bidirectional stream established")
            
            # Start a thread to receive commands
            def receive_commands():
                try:
                    print("[DEBUG] Command receiver thread started")
                    for command in response_iterator:
                        print(f"[DEBUG] Received command: agent_id={command.agent_id}, type={command.type}")
                        
                        if self.command_handler:
                            # Call the command handler
                            self.command_handler(command)
                        else:
                            print(f"[WARN] No command handler registered, ignoring command")
                            
                except Exception as e:
                    print(f"[DEBUG] Command receiving stopped: {e}")
            
            command_thread = threading.Thread(target=receive_commands, daemon=True)
            command_thread.start()
            
            # Wait for command thread (it runs until stream closes)
            command_thread.join()
            
        except Exception as e:
            print(f"[ERROR] Error in gRPC stream: {e}")
            import traceback
            traceback.print_exc()
            raise

"""
gRPC module - handles communication with the centralized server
"""

import grpc
from typing import Iterator
from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


class GrpcClient:
    """Handles gRPC communication with the monitoring server"""

    def __init__(self, server_address: str, hostname: str):
        """
        Initialize gRPC client

        Args:
            server_address: Address of the gRPC server (host:port)
        """
        self.client_hostname = hostname
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self.connected = False

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

    def stream_metrics(
        self, metrics_generator: Iterator[monitoring_pb2.MetricsRequest]
    ):
        """
        Stream metrics to server (bidirectional streaming)

        Args:
            metrics_generator: Generator that yields MetricsRequest messages
        """
        if not self.connected:
            raise RuntimeError("Not connected to gRPC server. Call connect() first.")
        try:
            response_stream = self.stub.StreamMetrics(metrics_generator, metadata=[('hostname', self.client_hostname)])
            
            # Consume responses to keep the stream alive
            for cmd in response_stream:
                print(f"Received command: {cmd}")
                
        except Exception as e:
            print(f"Error in gRPC stream: {e}")
            raise

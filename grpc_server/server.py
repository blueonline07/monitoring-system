"""
gRPC Server - Broker between Agents and Kafka
- Receives metrics from agents via client streaming
- Forwards metrics to Kafka
"""

import os
import grpc
from concurrent import futures
import dotenv
dotenv.load_dotenv()

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from grpc_server.kafka_producer import KafkaProducerService


class MonitoringServiceServicer(monitoring_pb2_grpc.MonitoringServiceServicer):
    """gRPC service implementation for receiving monitoring data from agents"""

    def __init__(
        self, kafka_producer: KafkaProducerService, kafka_bootstrap_servers: str
    ):
        """
        Initialize the monitoring service

        Args:
            kafka_producer: Kafka producer service for forwarding data
            kafka_bootstrap_servers: Kafka bootstrap servers
        """
        self.kafka_producer = kafka_producer
        self.kafka_bootstrap_servers = kafka_bootstrap_servers

    def StreamMetrics(self, request_iterator, context):
        """
        Client streaming: Agent sends metrics
        - Receives: stream MetricsRequest (periodic data from agent)
        - Forwards metrics to Kafka
        """
        from google.protobuf import empty_pb2

        agent_id = None

        try:
            for request in request_iterator:
                if agent_id is None:
                    agent_id = request.agent_id
                    print(f"✓ Agent connected: {agent_id}")

                # Forward metrics to Kafka
                self.kafka_producer.send_monitoring_data(
                    agent_id=agent_id,
                    timestamp=request.timestamp,
                    metrics={
                        "cpu_percent": request.metrics.cpu_percent,
                        "memory_percent": request.metrics.memory_percent,
                        "memory_used_mb": request.metrics.memory_used_mb,
                        "memory_total_mb": request.metrics.memory_total_mb,
                        "disk_read_mb": request.metrics.disk_read_mb,
                        "disk_write_mb": request.metrics.disk_write_mb,
                        "net_in_mb": request.metrics.net_in_mb,
                        "net_out_mb": request.metrics.net_out_mb,
                    },
                    metadata=dict(request.metadata),
                )
        except Exception as e:
            print(f"✗ Stream error for agent {agent_id}: {e}")
        finally:
            if agent_id:
                print(f"✓ Agent disconnected: {agent_id}")

        # Return empty response
        return empty_pb2.Empty()


_server_servicer = None


def serve(
    port: int = None,
    kafka_bootstrap_servers: str = None,
):
    """
    Start the gRPC server

    Args:
        port: Port to listen on (defaults to GRPC_SERVER_PORT env var or 50051)
        kafka_bootstrap_servers: Kafka bootstrap servers (defaults to KAFKA_BOOTSTRAP_SERVERS env var or localhost:9092)
    """
    if port is None:
        port = int(os.getenv("GRPC_SERVER_PORT", "50051"))
    if kafka_bootstrap_servers is None:
        kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    global _server_servicer

    # Initialize Kafka producer
    kafka_producer = KafkaProducerService(bootstrap_servers=kafka_bootstrap_servers)

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    _server_servicer = MonitoringServiceServicer(
        kafka_producer, kafka_bootstrap_servers
    )
    monitoring_pb2_grpc.add_MonitoringServiceServicer_to_server(
        _server_servicer, server
    )
    server.add_insecure_port(f"[::]:{port}")

    server.start()
    print(f"✓ gRPC Server running on port {port}")
    print(f"✓ Kafka: {kafka_bootstrap_servers}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.stop(0)
        kafka_producer.close()


def get_server_servicer():
    """Get the global server servicer instance"""
    return _server_servicer


if __name__ == "__main__":
    serve()

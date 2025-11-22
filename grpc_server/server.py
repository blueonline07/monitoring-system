"""
gRPC Server - Receives monitoring data from agents and forwards to Kafka (with streaming)
"""

import grpc
from concurrent import futures
import threading
import queue
from typing import Dict

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from grpc_server.kafka_producer import KafkaProducerService


class MonitoringServiceServicer(monitoring_pb2_grpc.MonitoringServiceServicer):
    """gRPC service implementation for receiving monitoring data from agents"""

    def __init__(self, kafka_producer: KafkaProducerService):
        """
        Initialize the monitoring service

        Args:
            kafka_producer: Kafka producer service for forwarding data
        """
        self.kafka_producer = kafka_producer
        # Store command queues for each agent
        self.agent_command_queues: Dict[str, queue.Queue] = {}
        print("✓ MonitoringServiceServicer initialized")

    def StreamMetrics(self, request_iterator, context):
        """
        Bidirectional streaming: receive metrics from agent, send commands to agent

        Args:
            request_iterator: Iterator of MetricsRequest from agent
            context: gRPC context

        Yields:
            Command for the agent
        """
        print("\n🔵 StreamMetrics called!")
        agent_id = None
        command_queue = queue.Queue()

        try:
            for request in request_iterator:
                try:
                    # Get agent ID from first request
                    if agent_id is None:
                        agent_id = request.agent_id
                        self.agent_command_queues[agent_id] = command_queue
                        print(f"\n✓ Agent connected (streaming): {agent_id}")

                    # Process metrics
                    timestamp = request.timestamp

                    print("\n[Metrics Received - Stream]")
                    print(f"  Agent: {agent_id}")
                    print(f"  CPU: {request.metrics.cpu_percent:.2f}%")
                    print(f"  Memory: {request.metrics.memory_percent:.2f}%")

                    # Send to Kafka
                    success = self.kafka_producer.send_monitoring_data(
                        agent_id=agent_id,
                        timestamp=timestamp,
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

                    if success:
                        print("✓ Forwarded to Kafka topic: monitoring-data")
                    else:
                        print("✗ Failed to forward to Kafka")

                    # Check for commands to send to agent
                    try:
                        # Non-blocking check for commands
                        command = command_queue.get_nowait()
                        print(f"\n📤 Sending command to agent {agent_id}")
                        yield command
                    except queue.Empty:
                        # No commands to send
                        pass

                except Exception as e:
                    print(f"\n✗ Error processing request: {type(e).__name__}: {e}")
                    import traceback

                    traceback.print_exc()
                    raise

        except grpc.RpcError as e:
            print(f"\n✗ Stream error for agent {agent_id}: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error in StreamMetrics: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Cleanup when agent disconnects
            if agent_id and agent_id in self.agent_command_queues:
                del self.agent_command_queues[agent_id]
                print(f"\n✓ Agent disconnected: {agent_id}")

    def send_command_to_agent(self, agent_id: str, command_type: int) -> bool:
        """
        Send a command to a specific agent

        Args:
            agent_id: Target agent ID
            command_type: Type of command (START or STOP)

        Returns:
            True if command was queued, False if agent not connected
        """
        if agent_id in self.agent_command_queues:
            # Create command
            command = monitoring_pb2.Command(agent_id=agent_id, type=command_type)
            self.agent_command_queues[agent_id].put(command)
            cmd_name = "START" if command_type == monitoring_pb2.START else "STOP"
            print(f"✓ Command queued for agent {agent_id}: {cmd_name}")
            return True
        else:
            print(f"✗ Agent {agent_id} not connected")
            return False


# Global server instance to access from command sender
_server_servicer = None


def serve(
    port: int = 50051,
    kafka_bootstrap_servers: str = "localhost:9092",
):
    """
    Start the gRPC server

    Args:
        port: Port to listen on
        kafka_bootstrap_servers: Kafka bootstrap servers
    """
    global _server_servicer

    # Initialize Kafka producer
    kafka_producer = KafkaProducerService(bootstrap_servers=kafka_bootstrap_servers)

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    _server_servicer = MonitoringServiceServicer(kafka_producer)
    monitoring_pb2_grpc.add_MonitoringServiceServicer_to_server(
        _server_servicer, server
    )
    server.add_insecure_port(f"[::]:{port}")

    print("=" * 60)
    print("gRPC Server Starting (Streaming Mode)")
    print("=" * 60)
    print(f"  Port: {port}")
    print(f"  Kafka: {kafka_bootstrap_servers}")
    print("=" * 60)
    print()

    server.start()
    print("✓ gRPC Server is running...")
    print("  Waiting for agent connections...")
    print()

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

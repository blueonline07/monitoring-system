"""
gRPC Server - Receives monitoring data from agents and forwards to Kafka
"""

import grpc
from concurrent import futures

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from grpc_server.kafka_producer import KafkaProducerService


class MonitoringServiceServicer(monitoring_pb2_grpc.MonitoringServiceServicer):
    """gRPC service implementation for receiving monitoring data from agents"""

    def __init__(self, kafka_producer: KafkaProducerService):
        """
        Initialize the monitoring service

        Args:
            kafka_producer: Kafka producer wrapper for forwarding data
        """
        self.kafka_producer = kafka_producer
        print("✓ MonitoringServiceServicer initialized")

    def SendMetrics(self, request, context):
        """
        Receive metrics from agent and forward to Kafka

        Args:
            request: MetricsRequest from agent
            context: gRPC context

        Returns:
            MetricsResponse
        """
        try:
            agent_id = request.agent_id
            hostname = request.hostname
            timestamp = request.timestamp

            print("\n[Metrics Received]")
            print(f"  Agent: {agent_id}")
            print(f"  Hostname: {hostname}")
            print(f"  CPU: {request.metrics.cpu_percent:.2f}%")
            print(f"  Memory: {request.metrics.memory_percent:.2f}%")

            # Convert to dict for Kafka
            metrics_data = {
                "agent_id": agent_id,
                "hostname": hostname,
                "timestamp": timestamp,
                "metrics": {
                    "cpu_percent": request.metrics.cpu_percent,
                    "memory_percent": request.metrics.memory_percent,
                    "memory_used_mb": request.metrics.memory_used_mb,
                    "memory_total_mb": request.metrics.memory_total_mb,
                    "disk_read_mb": request.metrics.disk_read_mb,
                    "disk_write_mb": request.metrics.disk_write_mb,
                    "net_in_mb": request.metrics.net_in_mb,
                    "net_out_mb": request.metrics.net_out_mb,
                    "custom_metrics": dict(request.metrics.custom_metrics),
                },
                "metadata": dict(request.metadata),
            }

            # Send to Kafka
            success = self.kafka_producer.send_monitoring_data(metrics_data)

            if success:
                print("✓ Forwarded to Kafka topic: monitoring-data")
                return monitoring_pb2.MetricsResponse(
                    success=True,
                    message="Metrics received and forwarded to Kafka",
                )
            else:
                print("✗ Failed to forward to Kafka")
                return monitoring_pb2.MetricsResponse(
                    success=False,
                    message="Failed to forward metrics to Kafka",
                )

        except Exception as e:
            print(f"✗ Error processing metrics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return monitoring_pb2.MetricsResponse(
                success=False,
                message=f"Error: {str(e)}",
            )

    def RegisterAgent(self, request, context):
        """
        Handle agent registration

        Args:
            request: AgentRegistration from agent
            context: gRPC context

        Returns:
            Ack
        """
        try:
            agent_id = request.agent_id
            hostname = request.hostname

            print("\n[Agent Registered]")
            print(f"  Agent: {agent_id}")
            print(f"  Hostname: {hostname}")

            # Send to Kafka agent-status topic
            agent_status = {
                "agent_id": agent_id,
                "hostname": hostname,
                "status": "registered",
                "timestamp": request.timestamp,
                "metadata": dict(request.metadata),
            }

            success = self.kafka_producer.send_agent_status(agent_status)

            if success:
                print("✓ Agent registration forwarded to Kafka")
                return monitoring_pb2.Ack(
                    success=True,
                    message="Agent registered successfully",
                )
            else:
                print("✗ Failed to forward registration to Kafka")
                return monitoring_pb2.Ack(
                    success=False,
                    message="Failed to register agent",
                )

        except Exception as e:
            print(f"✗ Error registering agent: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return monitoring_pb2.Ack(
                success=False,
                message=f"Error: {str(e)}",
            )


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
    # Initialize Kafka producer
    kafka_producer = KafkaProducerService(bootstrap_servers=kafka_bootstrap_servers)

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    monitoring_pb2_grpc.add_MonitoringServiceServicer_to_server(
        MonitoringServiceServicer(kafka_producer), server
    )
    server.add_insecure_port(f"[::]:{port}")

    print("=" * 60)
    print("gRPC Server Starting")
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


if __name__ == "__main__":
    serve()

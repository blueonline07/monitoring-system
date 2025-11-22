"""
gRPC Server - Receives data from agents via bidirectional streaming and forwards to Kafka
"""

import grpc
from concurrent import futures
import time
import sys
import os
from typing import Generator
import threading

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import generated gRPC code from shared module
from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from shared.kafka_schemas import KafkaTopics

# Import Kafka producer
from .kafka_producer import KafkaProducerService


class MonitoringService(monitoring_pb2_grpc.MonitoringServiceServicer):
    """gRPC service that receives agent data via streaming and forwards to Kafka"""

    def __init__(self, kafka_bootstrap_servers: str = "localhost:9092"):
        """
        Initialize monitoring service

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers address
        """
        self.kafka_producer = KafkaProducerService(kafka_bootstrap_servers)
        self.active_agents = {}  # agent_id -> agent info
        self.lock = threading.Lock()

    def RegisterAgent(self, request, context):
        """
        Register agent with server

        Args:
            request: AgentRegistration message
            context: gRPC context

        Returns:
            Ack message
        """
        with self.lock:
            self.active_agents[request.agent_id] = {
                "hostname": request.hostname,
                "os_type": request.os_type,
                "registered_at": time.time(),
            }

        print(f"✓ Agent registered: {request.agent_id} on {request.hostname}")

        # Send agent status to Kafka
        self.kafka_producer.send_agent_status(
            agent_id=request.agent_id,
            hostname=request.hostname,
            status="initializing",
        )

        return monitoring_pb2.Ack(
            success=True, message="Agent registered successfully"
        )

    def StreamCommunication(
        self, request_iterator: Generator[monitoring_pb2.AgentMessage, None, None], context
    ) -> Generator[monitoring_pb2.ServerMessage, None, None]:
        """
        Bidirectional streaming between agent and server

        Args:
            request_iterator: Stream of AgentMessage from agent
            context: gRPC context

        Yields:
            ServerMessage to agent
        """
        agent_id = None
        metrics_count = 0

        try:
            for agent_message in request_iterator:
                # Handle metrics data
                if agent_message.HasField("metrics_data"):
                    metrics_data = agent_message.metrics_data
                    agent_id = metrics_data.agent_id

                    # Convert protobuf metrics to dict
                    metrics_dict = {
                        "cpu_percent": metrics_data.metrics.cpu_percent,
                        "memory_percent": metrics_data.metrics.memory_percent,
                        "memory_used_mb": metrics_data.metrics.memory_used_mb,
                        "memory_total_mb": metrics_data.metrics.memory_total_mb,
                        "disk_read_mb": metrics_data.metrics.disk_read_mb,
                        "disk_write_mb": metrics_data.metrics.disk_write_mb,
                        "net_in_mb": metrics_data.metrics.net_in_mb,
                        "net_out_mb": metrics_data.metrics.net_out_mb,
                        "custom_metrics": dict(metrics_data.metrics.custom_metrics),
                    }

                    metadata_dict = dict(metrics_data.metadata)

                    # Send to Kafka
                    success = self.kafka_producer.send_monitoring_data(
                        agent_id=metrics_data.agent_id,
                        hostname=metrics_data.hostname,
                        timestamp=metrics_data.timestamp,
                        metrics=metrics_dict,
                        metadata=metadata_dict,
                    )

                    metrics_count += 1

                    if success:
                        print(
                            f"✓ Forwarded metrics #{metrics_count} from agent '{agent_id}' to Kafka"
                        )
                        # Send acknowledgment back to agent
                        yield monitoring_pb2.ServerMessage(
                            acknowledgment=monitoring_pb2.Ack(
                                success=True,
                                message=f"Metrics #{metrics_count} received and forwarded",
                            )
                        )
                    else:
                        yield monitoring_pb2.ServerMessage(
                            acknowledgment=monitoring_pb2.Ack(
                                success=False, message="Failed to forward to Kafka"
                            )
                        )

                # Handle command responses
                elif agent_message.HasField("command_response"):
                    response = agent_message.command_response
                    agent_id = response.agent_id

                    print(
                        f"✓ Command response from {agent_id}: {response.command_id}"
                    )

                    # Forward response to Kafka
                    self.kafka_producer.send_command_response(
                        command_id=response.command_id,
                        agent_id=response.agent_id,
                        success=response.success,
                        message=response.message,
                        result=dict(response.result),
                    )

                    # Acknowledge receipt
                    yield monitoring_pb2.ServerMessage(
                        acknowledgment=monitoring_pb2.Ack(
                            success=True, message="Command response received"
                        )
                    )

                # Handle heartbeats
                elif agent_message.HasField("heartbeat"):
                    heartbeat = agent_message.heartbeat
                    agent_id = heartbeat.agent_id

                    # Update agent status
                    with self.lock:
                        if agent_id in self.active_agents:
                            self.active_agents[agent_id]["last_heartbeat"] = (
                                time.time()
                            )

                    # Optional: Send heartbeat status to Kafka
                    # self.kafka_producer.send_agent_status(...)

                    # TODO: Check for pending commands from Kafka and send to agent
                    # For now, just acknowledge
                    # yield monitoring_pb2.ServerMessage(
                    #     acknowledgment=monitoring_pb2.Ack(
                    #         success=True, message="Heartbeat received"
                    #     )
                    # )

        except Exception as e:
            print(f"✗ Error in bidirectional stream for agent '{agent_id}': {e}")
            yield monitoring_pb2.ServerMessage(
                acknowledgment=monitoring_pb2.Ack(success=False, message=str(e))
            )

        finally:
            if agent_id:
                print(f"✓ Stream ended for agent '{agent_id}' ({metrics_count} metrics received)")
                # Update agent status
                with self.lock:
                    if agent_id in self.active_agents:
                        self.active_agents[agent_id]["status"] = "disconnected"


def serve(port: str = "50051", kafka_bootstrap_servers: str = "localhost:9092"):
    """
    Start the gRPC server

    Args:
        port: Port to listen on
        kafka_bootstrap_servers: Kafka bootstrap servers address
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Create and add monitoring service
    monitoring_service = MonitoringService(kafka_bootstrap_servers)
    monitoring_pb2_grpc.add_MonitoringServiceServicer_to_server(
        monitoring_service, server
    )

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    print("=" * 70)
    print("gRPC Server Started (Bidirectional Streaming)")
    print("=" * 70)
    print(f"  Port: {port}")
    print(f"  Kafka: {kafka_bootstrap_servers}")
    print(f"  Kafka topic: {KafkaTopics.MONITORING_DATA}")
    print(f"  Mode: Bidirectional streaming (no polling)")
    print(f"  Waiting for agent connections...")
    print("=" * 70)
    print()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop(0)
        monitoring_service.kafka_producer.close()


def main():
    """Main entry point for running the gRPC server"""
    import argparse

    parser = argparse.ArgumentParser(
        description="gRPC Monitoring Server (Bidirectional Streaming)"
    )
    parser.add_argument(
        "--port",
        type=str,
        default="50051",
        help="Port to listen on",
    )
    parser.add_argument(
        "--kafka",
        type=str,
        default="localhost:9092",
        help="Kafka bootstrap servers",
    )

    args = parser.parse_args()

    serve(port=args.port, kafka_bootstrap_servers=args.kafka)


if __name__ == "__main__":
    main()

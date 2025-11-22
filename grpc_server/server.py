"""
gRPC Server - Broker between Agents and Kafka
- Receives metrics from agents via bidirectional streaming
- Forwards metrics to Kafka
- Consumes commands from Kafka
- Forwards commands to agents via bidirectional streaming
"""

import grpc
from concurrent import futures
import queue
import threading
import json
from typing import Dict

from confluent_kafka import Consumer

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from shared.config import KafkaTopics
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
            kafka_bootstrap_servers: Kafka bootstrap servers for command consumer
        """
        self.kafka_producer = kafka_producer
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.agent_command_queues: Dict[str, queue.Queue] = {}
        self._stop_command_consumer = threading.Event()

    def StreamMetrics(self, request_iterator, context):
        """
        Bidirectional streaming: Agent sends metrics, Server sends commands
        - Receives: stream MetricsRequest (periodic data from agent)
        - Sends: stream Command (commands from Kafka/analysis app)
        """
        agent_id = None
        command_queue = queue.Queue()
        received_metrics = queue.Queue()
        stop_threads = threading.Event()

        def process_requests():
            """Background thread to process incoming requests from agent"""
            nonlocal agent_id
            try:
                for request in request_iterator:
                    if agent_id is None:
                        agent_id = request.agent_id
                        self.agent_command_queues[agent_id] = command_queue
                        print(f"✓ Agent connected: {agent_id}")

                    received_metrics.put(request)
            except Exception as e:
                print(f"\n✗ Error in request processor: {e}")
            finally:
                stop_threads.set()

        # Start request processor thread
        request_thread = threading.Thread(target=process_requests, daemon=True)
        request_thread.start()

        try:
            while not stop_threads.is_set():
                # Process metrics from agent -> forward to Kafka
                try:
                    request = received_metrics.get(timeout=0.1)

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
                except queue.Empty:
                    pass

                # Send commands from Kafka to agent
                try:
                    command = command_queue.get_nowait()
                    yield command
                except queue.Empty:
                    pass

        except Exception as e:
            print(f"✗ Stream error for agent {agent_id}: {e}")
        finally:
            stop_threads.set()
            if agent_id and agent_id in self.agent_command_queues:
                del self.agent_command_queues[agent_id]
                print(f"✓ Agent disconnected: {agent_id}")

    def send_command_to_agent(
        self, agent_id: str, command_type: int, parameters: dict = None
    ) -> bool:
        """Queue command to be sent to agent via bidirectional stream"""
        if agent_id not in self.agent_command_queues:
            return False

        command = monitoring_pb2.Command(agent_id=agent_id, type=command_type)
        if parameters:
            command.parameters.update(parameters)
        self.agent_command_queues[agent_id].put(command)
        return True

    def start_command_consumer(self):
        """Start Kafka consumer to receive commands from analysis app"""

        def consume_commands():
            consumer = Consumer(
                {
                    "bootstrap.servers": self.kafka_bootstrap_servers,
                    "group.id": "grpc-server-command-consumer",
                    "auto.offset.reset": "latest",
                }
            )
            consumer.subscribe([KafkaTopics.COMMANDS])

            while not self._stop_command_consumer.is_set():
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                if msg.error():
                    # Ignore topic not found (will be created when producer writes)
                    if hasattr(msg.error(), "code") and msg.error().code() == 3:
                        continue
                    continue

                try:
                    command_data = json.loads(msg.value().decode("utf-8"))
                    agent_id = command_data.get("agent_id")
                    command_type_str = command_data.get("type", "").upper()

                    # Handle commands here when needed
                    # Currently no commands are implemented
                except Exception:
                    pass

            consumer.close()

        threading.Thread(target=consume_commands, daemon=True).start()

    def stop_command_consumer(self):
        """Stop the command consumer"""
        self._stop_command_consumer.set()


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

    _server_servicer.start_command_consumer()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        _server_servicer.stop_command_consumer()
        server.stop(0)
        kafka_producer.close()


def get_server_servicer():
    """Get the global server servicer instance"""
    return _server_servicer


if __name__ == "__main__":
    serve()

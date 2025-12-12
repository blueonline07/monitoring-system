"""
gRPC Server - Broker between Agents and Kafka
- Receives metrics from agents via client streaming
- Forwards metrics to Kafka
"""

import grpc
import threading
import json
from concurrent import futures
from config import Config
from protobuf import monitoring_pb2, monitoring_pb2_grpc
from confluent_kafka import Producer, Consumer


class MonitoringServicer(monitoring_pb2_grpc.MonitoringServicer):
    """gRPC service implementation for receiving monitoring data from agents"""

    def __init__(self, kafka_producer: Producer, kafka_consumer: Consumer):
        """
        Initialize the monitoring service

        Args:
            kafka_producer: Kafka producer service for forwarding data
            kafka_bootstrap_servers: Kafka bootstrap servers
        """
        self.producer = kafka_producer
        self.consumer = kafka_consumer
        self.consumer.subscribe([Config.COMMAND_TOPIC])
        self.agents = {}
        self.lock = threading.Lock()

    def StreamMetrics(self, request_iterator, context):
        """
        Client streaming: Agent sends metrics
        - Receives: stream MetricsRequest (periodic data from agent)
        - Forwards metrics to Kafka
        """
        try:
            for request in request_iterator:
                self.producer.produce(
                    Config.MONITORING_TOPIC,
                    key=request.hostname.encode("utf-8"),
                    value=json.dumps(
                        {
                            "hostname": request.hostname,
                            "timestamp": request.timestamp,
                            "metrics": {
                                "cpu_percent": request.metrics.cpu_percent,
                                "memory_percent": request.metrics.memory_percent,
                                "memory_used_mb": request.metrics.memory_used_mb,
                                "memory_total_mb": request.metrics.memory_total_mb,
                                "disk_read_mb": request.metrics.disk_read_mb,
                                "disk_write_mb": request.metrics.disk_write_mb,
                                "net_in_mb": request.metrics.net_in_mb,
                                "net_out_mb": request.metrics.net_out_mb,
                            },
                            "metadata": dict(request.metadata),
                        }
                    ).encode("utf-8"),
                )
                self.producer.flush()
                yield monitoring_pb2.Command(agent="haha")

        except Exception as e:
            print(f"Error processing requests: {e}")


def serve(port):
    """
    Start the gRPC server

    Args:
        port: Port to listen on (defaults to GRPC_SERVER_PORT env var or 50051)
        kafka_bootstrap_servers: Kafka bootstrap servers (defaults to KAFKA_BOOTSTRAP_SERVERS env var or localhost:9092)
    """
    producer = Producer(
        {
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER,
        }
    )
    consumer = Consumer(
        {
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER,
            "group.id": Config.COMMAND_GROUP_ID,
            "auto.offset.reset": "earliest",
        }
    )

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    _server_servicer = MonitoringServicer(producer, consumer)
    monitoring_pb2_grpc.add_MonitoringServicer_to_server(_server_servicer, server)
    server.add_insecure_port(f"[::]:{port}")

    server.start()
    print(f"gRPC Server running on port {port}")
    print(f"Kafka: {Config.KAFKA_BOOTSTRAP_SERVER}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.stop(0)

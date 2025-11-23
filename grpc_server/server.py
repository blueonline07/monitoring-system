"""
gRPC Server - Broker between Agents and Kafka (with bidirectional streaming)
- Receives metrics from agents via bidirectional streaming
- Forwards metrics to Kafka
- Receives commands from Kafka
- Forwards commands to agents via bidirectional streaming
"""

import os
import grpc
import json
import time
import threading
import queue
from concurrent import futures
from typing import Dict
import dotenv
dotenv.load_dotenv()

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc
from grpc_server.kafka_producer import KafkaProducerService
from confluent_kafka import Consumer, KafkaError


class MonitoringServiceServicer(monitoring_pb2_grpc.MonitoringServiceServicer):
    """gRPC service implementation with bidirectional streaming"""

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
        
        # Command queues per agent (agent_id -> queue)
        self.agent_command_queues: Dict[str, queue.Queue] = {}
        self._queue_lock = threading.Lock()
        
        # Start Kafka command consumer thread
        self.running = True
        self.command_consumer_thread = threading.Thread(
            target=self._consume_commands, daemon=True
        )
        self.command_consumer_thread.start()
        print("✓ Command consumer thread started")

    def _consume_commands(self):
        """
        Consume commands from Kafka and queue them for agents
        """
        print("[DEBUG] Starting Kafka command consumer...")
        
        consumer = Consumer({
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'group.id': 'grpc-server-command-consumer',
            'auto.offset.reset': 'latest'
        })
        
        consumer.subscribe(['commands'])
        print(f"[DEBUG] Subscribed to 'commands' topic")
        
        while self.running:
            try:
                msg = consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"[ERROR] Kafka consumer error: {msg.error()}")
                        continue
                
                # Parse command
                command_data = json.loads(msg.value().decode('utf-8'))
                print(f"[DEBUG] Received command from Kafka: {command_data}")
                
                agent_id = command_data.get('agent_id')
                command_type = command_data.get('type', 'STATUS')
                params = command_data.get('params', {})
                timestamp = command_data.get('timestamp', int(time.time()))
                
                # Create Command protobuf message
                command_type_enum = getattr(
                    monitoring_pb2.CommandType, 
                    command_type, 
                    monitoring_pb2.CommandType.STATUS
                )
                
                command = monitoring_pb2.Command(
                    agent_id=agent_id,
                    type=command_type_enum,
                    timestamp=timestamp
                )
                command.params.update(params)
                
                # Queue command for agent
                with self._queue_lock:
                    if agent_id in self.agent_command_queues:
                        self.agent_command_queues[agent_id].put(command)
                        print(f"[DEBUG] Queued command for agent {agent_id}: {command_type}")
                    else:
                        print(f"[WARN] No active connection for agent {agent_id}")
                        
            except Exception as e:
                print(f"[ERROR] Command consumer error: {e}")
                import traceback
                traceback.print_exc()
        
        consumer.close()
        print("[DEBUG] Command consumer stopped")

    def StreamMetrics(self, request_iterator, context):
        """
        Bidirectional streaming: Agent sends metrics, receives commands
        - Receives: stream MetricsRequest (periodic data from agent)
        - Sends: stream Command (commands for agent)
        - Forwards metrics to Kafka
        """
        agent_id = None
        command_queue = queue.Queue()
        
        try:
            # Process first request to get agent_id
            first_request = next(request_iterator)
            agent_id = first_request.agent_id
            print(f"[DEBUG] Agent connected: {agent_id}")
            
            # Register agent's command queue
            with self._queue_lock:
                self.agent_command_queues[agent_id] = command_queue
            print(f"[DEBUG] Registered command queue for agent {agent_id}")
            
            # Forward first metrics to Kafka
            self._forward_metrics_to_kafka(first_request)
            
            # Start a thread to receive metrics
            def receive_metrics():
                try:
                    for request in request_iterator:
                        print(f"[DEBUG] Received metrics from {request.agent_id}")
                        self._forward_metrics_to_kafka(request)
                except Exception as e:
                    print(f"[DEBUG] Metrics receiving stopped for {agent_id}: {e}")
            
            metrics_thread = threading.Thread(target=receive_metrics, daemon=True)
            metrics_thread.start()
            
            # Send commands to agent as they arrive
            while context.is_active():
                try:
                    # Check for commands with timeout
                    command = command_queue.get(timeout=1.0)
                    print(f"[DEBUG] Sending command to agent {agent_id}: {command.type}")
                    yield command
                except queue.Empty:
                    # No command, continue waiting
                    continue
                    
        except StopIteration:
            print(f"[DEBUG] Agent {agent_id} closed stream")
        except Exception as e:
            import traceback
            print(f"[ERROR] Stream error for agent {agent_id}: {e}")
            print(f"Traceback: {traceback.format_exc()}")
        finally:
            # Cleanup: remove agent's command queue
            if agent_id:
                with self._queue_lock:
                    if agent_id in self.agent_command_queues:
                        del self.agent_command_queues[agent_id]
                print(f"[DEBUG] Agent disconnected: {agent_id}")

    def _forward_metrics_to_kafka(self, request):
        """Forward metrics to Kafka"""
        self.kafka_producer.send_monitoring_data(
            agent_id=request.agent_id,
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
    
    def SendCommand(self, request, context):
        """
        Send command to an agent (from external clients)
        - Receives: Command
        - Returns: CommandResponse
        """
        print(f"[DEBUG] SendCommand called for agent {request.agent_id}, type={request.type}")
        
        agent_id = request.agent_id
        
        # Queue command for agent
        with self._queue_lock:
            if agent_id in self.agent_command_queues:
                self.agent_command_queues[agent_id].put(request)
                print(f"[DEBUG] Command queued for agent {agent_id}")
                return monitoring_pb2.CommandResponse(
                    success=True,
                    message=f"Command queued for agent {agent_id}",
                    agent_id=agent_id,
                    timestamp=int(time.time())
                )
            else:
                print(f"[WARN] Agent {agent_id} not connected")
                return monitoring_pb2.CommandResponse(
                    success=False,
                    message=f"Agent {agent_id} not connected",
                    agent_id=agent_id,
                    timestamp=int(time.time())
                )
    
    def shutdown(self):
        """Shutdown the servicer"""
        print("[DEBUG] Shutting down servicer...")
        self.running = False


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
        _server_servicer.shutdown()
        server.stop(0)
        kafka_producer.close()


def get_server_servicer():
    """Get the global server servicer instance"""
    return _server_servicer


if __name__ == "__main__":
    serve()

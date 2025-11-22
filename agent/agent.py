"""
Monitor Agent - Collects system metrics and sends to gRPC Server via bidirectional streaming
"""

import grpc
import socket
import time
import random
import threading
from datetime import datetime
from typing import Optional, Generator
import sys
import os
import queue

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import generated gRPC code from shared module
from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


class MonitorAgent:
    """Monitor agent that collects and streams system metrics to gRPC server"""

    def __init__(
        self,
        agent_id: str,
        grpc_server_address: str = "localhost:50051",
        mode: str = "mock",
    ):
        """
        Initialize monitor agent

        Args:
            agent_id: Unique identifier for this agent
            grpc_server_address: Address of the gRPC server
            mode: "mock" for dummy data, "real" for actual system metrics
        """
        self.agent_id = agent_id
        self.hostname = socket.gethostname()
        self.grpc_server_address = grpc_server_address
        self.mode = mode
        self.channel: Optional[grpc.Channel] = None
        self.stub = None
        self.running = False
        self.message_queue = queue.Queue()

    def connect(self):
        """Establish gRPC connection to server"""
        self.channel = grpc.insecure_channel(self.grpc_server_address)
        self.stub = monitoring_pb2_grpc.MonitoringServiceStub(self.channel)
        print(f"✓ Connected to gRPC server at {self.grpc_server_address}")

    def register(self):
        """Register agent with server"""
        try:
            registration = monitoring_pb2.AgentRegistration(
                agent_id=self.agent_id,
                hostname=self.hostname,
                os_type=os.name,
                os_version=str(sys.platform),
                timestamp=int(datetime.now().timestamp()),
            )
            response = self.stub.RegisterAgent(registration)
            if response.success:
                print(f"✓ Agent registered: {response.message}")
            else:
                print(f"✗ Registration failed: {response.message}")
        except Exception as e:
            print(f"✗ Error during registration: {e}")

    def collect_metrics(self) -> monitoring_pb2.SystemMetrics:
        """
        Collect system metrics

        Returns:
            SystemMetrics protobuf message
        """
        if self.mode == "mock":
            return self._generate_mock_metrics()
        else:
            return self._collect_real_metrics()

    def _generate_mock_metrics(self) -> monitoring_pb2.SystemMetrics:
        """Generate mock system metrics with realistic random values"""
        return monitoring_pb2.SystemMetrics(
            cpu_percent=random.uniform(20.0, 80.0),
            memory_percent=random.uniform(40.0, 90.0),
            memory_used_mb=random.uniform(2000.0, 7000.0),
            memory_total_mb=8192.0,
            disk_read_mb=random.uniform(5.0, 50.0),
            disk_write_mb=random.uniform(2.0, 30.0),
            net_in_mb=random.uniform(1.0, 20.0),
            net_out_mb=random.uniform(0.5, 15.0),
            custom_metrics={},
        )

    def _collect_real_metrics(self) -> monitoring_pb2.SystemMetrics:
        """
        Collect real system metrics using psutil

        Returns:
            SystemMetrics protobuf message
        """
        try:
            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used_mb = mem.used / (1024 * 1024)
            memory_total_mb = mem.total / (1024 * 1024)

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
            disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0

            # Network I/O
            net_io = psutil.net_io_counters()
            net_in_mb = net_io.bytes_recv / (1024 * 1024) if net_io else 0
            net_out_mb = net_io.bytes_sent / (1024 * 1024) if net_io else 0

            return monitoring_pb2.SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_read_mb=disk_read_mb,
                disk_write_mb=disk_write_mb,
                net_in_mb=net_in_mb,
                net_out_mb=net_out_mb,
                custom_metrics={},
            )

        except ImportError:
            print("✗ psutil not installed. Using mock data instead.")
            return self._generate_mock_metrics()

    def generate_agent_messages(
        self, interval: int, iterations: int
    ) -> Generator[monitoring_pb2.AgentMessage, None, None]:
        """
        Generator that yields agent messages for streaming

        Args:
            interval: Collection interval in seconds
            iterations: Number of iterations (0 = infinite)

        Yields:
            AgentMessage containing metrics or responses
        """
        count = 0
        while self.running:
            # Check if we should stop
            if iterations > 0 and count >= iterations:
                print(f"\n✓ Completed {iterations} iterations. Stopping stream.")
                break

            # Send heartbeat
            heartbeat = monitoring_pb2.AgentHeartbeat(
                agent_id=self.agent_id,
                timestamp=int(datetime.now().timestamp()),
                status="running",
            )
            yield monitoring_pb2.AgentMessage(heartbeat=heartbeat)

            # Collect and send metrics
            metrics = self.collect_metrics()
            metrics_data = monitoring_pb2.MetricsData(
                agent_id=self.agent_id,
                hostname=self.hostname,
                timestamp=int(datetime.now().timestamp()),
                metrics=metrics,
                metadata={"os": os.name, "mode": self.mode},
            )

            agent_message = monitoring_pb2.AgentMessage(metrics_data=metrics_data)
            yield agent_message

            count += 1
            print(f"\n[{count}] Streamed metrics:")
            print(f"  CPU: {metrics.cpu_percent:.2f}%")
            print(f"  Memory: {metrics.memory_percent:.2f}%")

            # Check for any command responses to send
            try:
                while not self.message_queue.empty():
                    response = self.message_queue.get_nowait()
                    yield monitoring_pb2.AgentMessage(command_response=response)
            except queue.Empty:
                pass

            # Wait for next interval
            time.sleep(interval)

    def handle_server_messages(
        self, responses: Generator[monitoring_pb2.ServerMessage, None, None]
    ):
        """
        Handle incoming messages from server

        Args:
            responses: Generator of ServerMessage from server
        """
        try:
            for response in responses:
                if response.HasField("command"):
                    command = response.command
                    print(f"\n📩 Received command: {command.command_type}")
                    print(f"  Command ID: {command.command_id}")

                    # Process command (placeholder)
                    command_response = monitoring_pb2.CommandResponseMessage(
                        command_id=command.command_id,
                        agent_id=self.agent_id,
                        success=True,
                        message=f"Command {command.command_type} executed",
                        result={},
                        timestamp=int(datetime.now().timestamp()),
                    )

                    # Queue response to send back
                    self.message_queue.put(command_response)

                elif response.HasField("acknowledgment"):
                    ack = response.acknowledgment
                    if not ack.success:
                        print(f"✗ Server error: {ack.message}")

        except Exception as e:
            print(f"✗ Error handling server messages: {e}")

    def run(self, interval: int = 5, iterations: int = 0):
        """
        Main loop: establish bidirectional streaming with server

        Args:
            interval: Time between metric collections in seconds
            iterations: Number of messages to send (0 = infinite)
        """
        self.connect()
        self.register()

        print("=" * 60)
        print(f"Monitor Agent Started: {self.agent_id}")
        print("=" * 60)
        print(f"  Hostname: {self.hostname}")
        print(f"  Mode: {self.mode}")
        print(f"  gRPC Server: {self.grpc_server_address}")
        print(f"  Interval: {interval}s")
        print(f"  Iterations: {iterations if iterations > 0 else 'infinite'}")
        print(f"  Using bidirectional streaming")
        print("=" * 60)
        print()

        self.running = True

        try:
            # Start bidirectional streaming
            responses = self.stub.StreamCommunication(
                self.generate_agent_messages(interval, iterations)
            )

            # Handle server responses in main thread
            self.handle_server_messages(responses)

        except grpc.RpcError as e:
            print(f"\n✗ gRPC error: {e.code()} - {e.details()}")
        except KeyboardInterrupt:
            print("\n\nShutting down agent...")
        finally:
            self.running = False
            if self.channel:
                self.channel.close()


def main():
    """Main entry point for running the agent"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Agent (Bidirectional Streaming)")
    parser.add_argument(
        "--agent-id",
        type=str,
        default="agent-001",
        help="Unique agent identifier",
    )
    parser.add_argument(
        "--server",
        type=str,
        default="localhost:50051",
        help="gRPC server address",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["mock", "real"],
        default="mock",
        help="Data mode: mock or real",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Collection interval in seconds",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations (0 = infinite)",
    )

    args = parser.parse_args()

    # Create and run agent
    agent = MonitorAgent(
        agent_id=args.agent_id,
        grpc_server_address=args.server,
        mode=args.mode,
    )

    agent.run(interval=args.interval, iterations=args.iterations)


if __name__ == "__main__":
    main()

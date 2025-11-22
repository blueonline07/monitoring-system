"""
Monitor Agent - Collects system metrics and sends to gRPC Server
"""

import grpc
import socket
import time
import random
import os
from datetime import datetime
from typing import Optional

# Import generated gRPC code from shared module
from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


class MonitorAgent:
    """Monitor agent that collects and sends system metrics to gRPC server"""

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

    def connect(self):
        """Establish gRPC connection to server"""
        self.channel = grpc.insecure_channel(self.grpc_server_address)
        self.stub = monitoring_pb2_grpc.MonitoringServiceStub(self.channel)
        print(f"✓ Connected to gRPC server at {self.grpc_server_address}")

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

    def send_metrics(self) -> bool:
        """
        Send metrics to gRPC server

        Returns:
            True if successful, False otherwise
        """
        try:
            # Collect metrics
            metrics = self.collect_metrics()

            # Create metrics request
            request = monitoring_pb2.MetricsRequest(
                agent_id=self.agent_id,
                hostname=self.hostname,
                timestamp=int(datetime.now().timestamp()),
                metrics=metrics,
                metadata={
                    "os": os.name,
                    "mode": self.mode,
                },
            )

            # Send via gRPC
            response = self.stub.SendMetrics(request)

            if response.success:
                print("✓ Metrics sent successfully")
                print(f"  CPU: {metrics.cpu_percent:.2f}%")
                print(f"  Memory: {metrics.memory_percent:.2f}%")
                print(f"  Response: {response.message}")
                return True
            else:
                print(f"✗ Failed to send metrics: {response.message}")
                return False

        except grpc.RpcError as e:
            print(f"✗ gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print(f"✗ Error sending metrics: {e}")
            return False

    def run(self, interval: int = 5, iterations: int = 0):
        """
        Main loop: collect and send metrics periodically

        Args:
            interval: Time between sends in seconds
            iterations: Number of messages to send (0 = infinite)
        """
        self.connect()

        print("=" * 60)
        print(f"Monitor Agent Started: {self.agent_id}")
        print("=" * 60)
        print(f"  Hostname: {self.hostname}")
        print(f"  Mode: {self.mode}")
        print(f"  gRPC Server: {self.grpc_server_address}")
        print(f"  Interval: {interval}s")
        print(f"  Iterations: {iterations if iterations > 0 else 'infinite'}")
        print("=" * 60)
        print()

        try:
            count = 0
            while True:
                count += 1
                print(f"\n[{count}] Collecting and sending metrics...")

                # Send metrics
                self.send_metrics()

                # Check if we should stop
                if iterations > 0 and count >= iterations:
                    print(f"\n✓ Completed {iterations} iterations. Stopping.")
                    break

                # Wait for next interval
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nShutting down agent...")
        finally:
            if self.channel:
                self.channel.close()


def main():
    """Main entry point for running the agent"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Agent")
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

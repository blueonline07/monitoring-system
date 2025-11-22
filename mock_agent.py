"""
Simple Mock Agent - Generates and sends mock monitoring data with streaming and plugins
"""

import grpc
import socket
import time
import random
import threading
from datetime import datetime
from typing import Dict, Any

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


# ============================================================================
# Mock Agent with Streaming
# ============================================================================


class MockAgent:
    """Mock agent that generates data and sends via streaming"""

    def __init__(self, agent_id: str, server_address: str):
        self.agent_id = agent_id
        self.hostname = socket.gethostname()
        self.server_address = server_address

        # Configuration (can be updated by commands)
        self.interval = 5
        self.active_metrics = [
            "cpu",
            "memory",
            "disk_read",
            "disk_write",
            "net_in",
            "net_out",
        ]

        # Control flags
        self.running = False
        self.stop_event = threading.Event()

    def generate_mock_metrics(self) -> Dict[str, Any]:
        """Generate random mock system metrics"""
        all_metrics = {
            "cpu_percent": (
                random.uniform(20.0, 80.0) if "cpu" in self.active_metrics else 0.0
            ),
            "memory_percent": (
                random.uniform(40.0, 90.0) if "memory" in self.active_metrics else 0.0
            ),
            "memory_used_mb": (
                random.uniform(2000.0, 7000.0)
                if "memory" in self.active_metrics
                else 0.0
            ),
            "memory_total_mb": 8192.0,
            "disk_read_mb": (
                random.uniform(5.0, 50.0) if "disk_read" in self.active_metrics else 0.0
            ),
            "disk_write_mb": (
                random.uniform(2.0, 30.0)
                if "disk_write" in self.active_metrics
                else 0.0
            ),
            "net_in_mb": (
                random.uniform(1.0, 20.0) if "net_in" in self.active_metrics else 0.0
            ),
            "net_out_mb": (
                random.uniform(0.5, 15.0) if "net_out" in self.active_metrics else 0.0
            ),
        }

        return all_metrics

    def handle_command(self, command: monitoring_pb2.Command):
        """Handle incoming command from server"""
        cmd_type_name = "START" if command.type == monitoring_pb2.START else "STOP"
        print(f"\n📥 Command received: {cmd_type_name} for agent: {command.agent_id}")

        if command.type == monitoring_pb2.STOP:
            print("  ✓ Stopping collection")
            self.stop_event.set()
        elif command.type == monitoring_pb2.START:
            print("  ✓ Starting collection")
            self.stop_event.clear()

    def metrics_generator(self):
        """Generator that yields metrics at configured interval"""
        count = 0
        while self.running and not self.stop_event.is_set():
            count += 1
            print(f"\n[{count}] Generating metrics...")

            # Generate metrics
            metrics = self.generate_mock_metrics()

            print(f"  CPU: {metrics['cpu_percent']:.2f}%")
            print(f"  Memory: {metrics['memory_percent']:.2f}%")

            # Create protobuf message
            system_metrics = monitoring_pb2.SystemMetrics(
                cpu_percent=metrics["cpu_percent"],
                memory_percent=metrics["memory_percent"],
                memory_used_mb=metrics["memory_used_mb"],
                memory_total_mb=metrics["memory_total_mb"],
                disk_read_mb=metrics["disk_read_mb"],
                disk_write_mb=metrics["disk_write_mb"],
                net_in_mb=metrics["net_in_mb"],
                net_out_mb=metrics["net_out_mb"],
            )

            request = monitoring_pb2.MetricsRequest(
                agent_id=self.agent_id,
                timestamp=int(datetime.now().timestamp()),
                metrics=system_metrics,
                metadata={},
            )

            yield request

            # Wait for configured interval
            time.sleep(self.interval)

    def run_streaming(self):
        """Run agent with bidirectional streaming"""
        print("=" * 60)
        print(f"Mock Agent (Streaming): {self.agent_id}")
        print("=" * 60)
        print(f"  Hostname: {self.hostname}")
        print(f"  Server: {self.server_address}")
        print(f"  Initial interval: {self.interval}s")
        print(f"  Active metrics: {self.active_metrics}")
        print("=" * 60)
        print()

        # Connect to gRPC server
        channel = grpc.insecure_channel(self.server_address)
        stub = monitoring_pb2_grpc.MonitoringServiceStub(channel)

        print("✓ Connected to gRPC server")
        print("✓ Starting bidirectional stream...")
        print()

        self.running = True  # Set before creating generator!

        try:
            # Start bidirectional streaming
            response_stream = stub.StreamMetrics(self.metrics_generator())

            # Listen for commands
            for command in response_stream:
                if not self.running:
                    break
                self.handle_command(command)

        except grpc.RpcError as e:
            print(f"\n✗ gRPC Error: {e.code()} - {e.details()}")
        except KeyboardInterrupt:
            print("\n\n⚠ Keyboard interrupt received")
        finally:
            print("\n✓ Shutting down...")
            self.running = False
            self.stop_event.set()
            channel.close()
            print("✓ Disconnected")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Simple Mock Agent with Streaming")
    parser.add_argument(
        "--agent-id",
        type=str,
        default="agent-001",
        help="Agent identifier",
    )
    parser.add_argument(
        "--server",
        type=str,
        default="localhost:50051",
        help="gRPC server address",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Initial interval between sends (seconds)",
    )

    args = parser.parse_args()

    # Create and run agent
    agent = MockAgent(
        agent_id=args.agent_id,
        server_address=args.server,
    )
    agent.interval = args.interval

    agent.run_streaming()


if __name__ == "__main__":
    main()

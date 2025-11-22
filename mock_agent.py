"""
Monitoring Agent - Sends metrics via bidirectional streaming
"""

import grpc
import socket
import time
import random
from datetime import datetime
from typing import Dict, Any

from shared import monitoring_pb2
from shared import monitoring_pb2_grpc


class MockAgent:
    """Agent that sends periodic metrics and receives commands via bidirectional streaming"""

    def __init__(self, agent_id: str, server_address: str):
        self.agent_id = agent_id
        self.hostname = socket.gethostname()
        self.server_address = server_address
        self.interval = 5
        self.active_metrics = [
            "cpu",
            "memory",
            "disk_read",
            "disk_write",
            "net_in",
            "net_out",
        ]
        self.running = False

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
        """Handle command from server"""
        # Handle commands here when needed
        pass

    def metrics_generator(self):
        """Generator: sends periodic metrics"""
        while self.running:
            metrics = self.generate_mock_metrics()
            yield monitoring_pb2.MetricsRequest(
                agent_id=self.agent_id,
                timestamp=int(datetime.now().timestamp()),
                metrics=monitoring_pb2.SystemMetrics(
                    cpu_percent=metrics["cpu_percent"],
                    memory_percent=metrics["memory_percent"],
                    memory_used_mb=metrics["memory_used_mb"],
                    memory_total_mb=metrics["memory_total_mb"],
                    disk_read_mb=metrics["disk_read_mb"],
                    disk_write_mb=metrics["disk_write_mb"],
                    net_in_mb=metrics["net_in_mb"],
                    net_out_mb=metrics["net_out_mb"],
                ),
                metadata={},
            )
            time.sleep(self.interval)

    def run_streaming(self):
        """Run agent: send metrics via bidirectional stream, receive commands"""
        channel = grpc.insecure_channel(self.server_address)
        stub = monitoring_pb2_grpc.MonitoringServiceStub(channel)

        print(f"✓ Agent {self.agent_id} connected to {self.server_address}")
        self.running = True

        try:
            # Bidirectional streaming: send metrics, receive commands
            response_stream = stub.StreamMetrics(self.metrics_generator())
            for command in response_stream:
                if not self.running:
                    break
                self.handle_command(command)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            channel.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Monitoring Agent")
    parser.add_argument("--agent-id", type=str, default="agent-001", help="Agent ID")
    parser.add_argument(
        "--server", type=str, default="localhost:50051", help="gRPC server"
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Metrics interval (seconds)"
    )

    args = parser.parse_args()

    agent = MockAgent(args.agent_id, args.server)
    agent.interval = args.interval
    agent.run_streaming()


if __name__ == "__main__":
    main()

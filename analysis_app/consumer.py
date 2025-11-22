"""
Analysis Application - CLI tool to read metrics from Kafka and send commands
"""

from confluent_kafka import Consumer
import socket
import time
import json

from shared.config import KafkaTopics


class AnalysisApp:
    """Analysis application: reads metrics from Kafka, sends commands to Kafka"""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "analysis-app-group",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "security.protocol": "PLAINTEXT",
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "client.id": socket.gethostname(),
            }
        )
        self.consumer.subscribe([KafkaTopics.MONITORING_DATA])

    def display_metrics(self, data: dict):
        """Display metrics to stdout"""
        m = data.get("metrics", {})
        print(f"\n[{data.get('agent_id', 'unknown')}] {data.get('timestamp', '')}")
        print(
            f"  CPU: {m.get('cpu_percent', 0):.2f}% | Memory: {m.get('memory_percent', 0):.2f}%"
        )
        print(
            f"  Disk: R={m.get('disk_read_mb', 0):.2f}MB/s W={m.get('disk_write_mb', 0):.2f}MB/s"
        )
        print(
            f"  Network: In={m.get('net_in_mb', 0):.2f}MB/s Out={m.get('net_out_mb', 0):.2f}MB/s"
        )

    def get_all_metrics(self, timeout: float = 5.0):
        """Get all metrics from Kafka and display to stdout"""
        start_time = time.time()
        count = 0

        try:
            while time.time() - start_time < timeout:
                msg = self.consumer.poll(timeout=0.5)
                if msg is None or msg.error():
                    continue

                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    count += 1
                    self.display_metrics(data)
                except Exception:
                    pass

            if count == 0:
                print("⚠ No metrics found")
            else:
                print(f"\n✓ Retrieved {count} metric(s)")
        finally:
            self.consumer.close()


def main():
    """Main entry point for CLI application"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analysis Application CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all metrics from Kafka and display to stdout
  python3 run_analysis.py get-metrics

  # Get metrics with custom timeout
  python3 run_analysis.py get-metrics --timeout 10

  # Use custom Kafka server
  python3 run_analysis.py get-metrics --kafka localhost:9092
        """,
    )

    parser.add_argument(
        "--kafka",
        type=str,
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default="analysis-app-group",
        help="Consumer group ID (default: analysis-app-group)",
    )

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Subcommand: get-metrics
    get_metrics_parser = subparsers.add_parser(
        "get-metrics",
        help="Get all metrics from Kafka and display to stdout",
    )
    get_metrics_parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Maximum time to wait for messages in seconds (default: 5.0)",
    )

    args = parser.parse_args()

    app = AnalysisApp(
        bootstrap_servers=args.kafka,
        group_id=args.group_id,
    )

    if args.command == "get-metrics":
        app.get_all_metrics(timeout=args.timeout)
    return 0


if __name__ == "__main__":
    main()

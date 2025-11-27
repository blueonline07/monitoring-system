"""
Analysis Application - CLI tool to read metrics from Kafka
"""

from confluent_kafka import Consumer, Producer
import time
import json
from shared import Config


class AnalysisApp:
    """Analysis application: reads metrics from Kafka"""

    def __init__(self):
        self.consumer = Consumer(
            {
                "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER,
                "group.id": Config.KAFKA_GROUP_ID,
                "auto.offset.reset": "smallest",
            }
        )
        self.producer = Producer({"bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER})
        self.consumer.subscribe([Config.MONITORING_TOPIC])

    def display_metrics(self, data: dict):
        """Display metrics to stdout"""
        m = data.get("metrics", {})
        print(f"\n[{data.get('hostname', 'unknown')}] {data.get('timestamp', '')}")
        print(
            f"  CPU: {m.get('cpu_percent', 0):.2f}% | Memory: {m.get('memory_percent', 0):.2f}%"
        )
        print(
            f"  Disk: R={m.get('disk_read_mb', 0):.2f}MB/s W={m.get('disk_write_mb', 0):.2f}MB/s"
        )
        print(
            f"  Network: In={m.get('net_in_mb', 0):.2f}MB/s Out={m.get('net_out_mb', 0):.2f}MB/s"
        )

    def get_all_metrics(self, hostname: str, timeout: float = 5.0):
        """Get all metrics from Kafka and display to stdout"""
        start_time = time.time()
        count = 0

        try:
            while time.time() - start_time < timeout:
                msg = self.consumer.poll(timeout=0.5)
                if msg is None or msg.error():
                    continue
                if msg.key().decode("utf-8") != hostname:
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

    def send_command(self, hostname: str, content: str):

        self.producer.produce(
            Config.COMMAND_TOPIC,
            key=hostname,
            value=json.dumps(
                {
                    "hostname": hostname,
                    "content": content,
                    "timestamp": int(time.time()),
                }
            ),
        )
        self.producer.flush()


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

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Subcommand: get-metrics
    get_metrics_parser = subparsers.add_parser(
        "get-metrics",
        help="Get all metrics from Kafka and display to stdout",
    )
    get_metrics_parser.add_argument(
        "--hostname",
        type=str,
        required=True
    )

    send_command_parser = subparsers.add_parser(
        "send-command", help="send command to agent"
    )

    get_metrics_parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Maximum time to wait for messages in seconds (default: 5.0)",
    )
    send_command_parser.add_argument("--hostname", type=str, required=True)
    send_command_parser.add_argument("--content", type=str, default="")

    args = parser.parse_args()

    app = AnalysisApp()

    if args.command == "get-metrics":
        app.get_all_metrics(hostname=args.hostname, timeout=args.timeout)
    if args.command == "send-command":
        app.send_command(hostname=args.hostname, content=args.content)
    return 0


if __name__ == "__main__":
    main()

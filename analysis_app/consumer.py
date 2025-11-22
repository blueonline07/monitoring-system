"""
Analysis Application - Consumes and analyzes monitoring data from Kafka
"""

from confluent_kafka import Consumer
import socket
import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.kafka_schemas import KafkaTopics


class AnalysisApp:
    """Analysis application that consumes and displays monitoring data from Kafka"""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "analysis-app-group",
    ):
        """
        Initialize analysis application

        Args:
            bootstrap_servers: Kafka bootstrap servers address
            group_id: Consumer group ID
        """
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

        # Subscribe to monitoring-data topic
        self.consumer.subscribe([KafkaTopics.MONITORING_DATA])
        print(f"✓ Subscribed to Kafka topic: {KafkaTopics.MONITORING_DATA}")

    def display_metrics(self, data: dict):
        """
        Display monitoring data in a readable format

        Args:
            data: Monitoring data dictionary
        """
        agent_id = data.get("agent_id", "unknown")
        hostname = data.get("hostname", "unknown")
        timestamp = data.get("timestamp", "")
        metrics = data.get("metrics", {})
        metadata = data.get("metadata", {})

        print("\n" + "=" * 70)
        print(f"📊 MONITORING DATA RECEIVED")
        print("=" * 70)
        print(f"  Agent ID:   {agent_id}")
        print(f"  Hostname:   {hostname}")
        print(f"  Timestamp:  {timestamp}")
        print(f"  Mode:       {metadata.get('mode', 'N/A')}")
        print()
        print("📈 System Metrics:")
        print(f"  CPU Usage:       {metrics.get('cpu_percent', 0):.2f}%")
        print(f"  Memory Usage:    {metrics.get('memory_percent', 0):.2f}%")
        print(
            f"  Memory Used:     {metrics.get('memory_used_mb', 0):.2f} / {metrics.get('memory_total_mb', 0):.2f} MB"
        )
        print(f"  Disk Read:       {metrics.get('disk_read_mb', 0):.2f} MB/s")
        print(f"  Disk Write:      {metrics.get('disk_write_mb', 0):.2f} MB/s")
        print(f"  Network In:      {metrics.get('net_in_mb', 0):.2f} MB/s")
        print(f"  Network Out:     {metrics.get('net_out_mb', 0):.2f} MB/s")
        print("=" * 70)

    def process_metrics(self, data: dict):
        """
        Process monitoring metrics - override this for custom processing

        Args:
            data: Monitoring data dictionary
        """
        # Default implementation: just display
        self.display_metrics(data)

        # TODO: Add custom processing logic here
        # - Store in database
        # - Run analysis
        # - Trigger alerts based on thresholds
        # - Generate reports

    def run(self):
        """Main consumption loop"""
        print("=" * 70)
        print("Analysis Application Started")
        print("=" * 70)
        print(f"  Kafka: {self.bootstrap_servers}")
        print(f"  Group ID: {self.group_id}")
        print(f"  Topic: {KafkaTopics.MONITORING_DATA}")
        print("  Waiting for monitoring data...")
        print("  (Press Ctrl+C to stop)")
        print("=" * 70)

        try:
            message_count = 0
            while True:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    print(f"✗ Consumer error: {msg.error()}")
                    continue

                # Deserialize and process message
                try:
                    message_count += 1
                    data = json.loads(msg.value().decode("utf-8"))
                    print(f"\n[Message #{message_count}]")
                    self.process_metrics(data)

                except json.JSONDecodeError as e:
                    print(f"✗ Error decoding JSON message: {e}")
                except Exception as e:
                    print(f"✗ Error processing message: {e}")

        except KeyboardInterrupt:
            print("\n\nShutting down analysis app...")
        finally:
            self.consumer.close()
            print("✓ Consumer closed")


def main():
    """Main entry point for running the analysis application"""
    import argparse

    parser = argparse.ArgumentParser(description="Analysis Application")
    parser.add_argument(
        "--kafka",
        type=str,
        default="localhost:9092",
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default="analysis-app-group",
        help="Consumer group ID",
    )

    args = parser.parse_args()

    # Create and run analysis app
    app = AnalysisApp(
        bootstrap_servers=args.kafka,
        group_id=args.group_id,
    )

    app.run()


if __name__ == "__main__":
    main()

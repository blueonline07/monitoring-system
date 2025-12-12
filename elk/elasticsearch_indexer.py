import json
import signal
import sys
from typing import Dict, Any
from datetime import datetime, timedelta 
from confluent_kafka import Consumer
from shared import Config
from elk.elk_search import ElasticsearchClient


class ElasticsearchIndexer:
    """Consumer đọc từ Kafka và đánh index vào Elasticsearch"""

    def __init__(
        self,
        kafka_bootstrap_server: str = None,
        elasticsearch_host: str = "localhost",
        elasticsearch_port: int = 9200,
        index_name: str = "agent-metrics",
        consumer_group_id: str = "elasticsearch-indexer",
    ):
        """
        Initialize Elasticsearch Indexer
        """
        # Initialize Elasticsearch client
        self.es_client = ElasticsearchClient(
            host=elasticsearch_host, port=elasticsearch_port, index_name=index_name
        )

        # Initialize Kafka consumer
        kafka_server = kafka_bootstrap_server or Config.KAFKA_BOOTSTRAP_SERVER
        self.consumer = Consumer(
            {
                "bootstrap.servers": kafka_server,
                "group.id": consumer_group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 1000,
            }
        )
        self.consumer.subscribe([Config.MONITORING_TOPIC])

        self.running = False
        self.indexed_count = 0
        self.error_count = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.stop()

    def _parse_metric_data(self, kafka_data: Dict[str, Any]) -> Dict[str, Any]:
        hostname = kafka_data.get("hostname", "unknown")
        metrics = kafka_data.get("metrics", {})

        current_utc = datetime.utcnow()
        timestamp = int(current_utc.timestamp())
        
        print(f"DEBUG TIME: Đang index dữ liệu vào lúc {current_utc} (UTC) -> Timestamp số: {timestamp}")

        agent_id = 0
        try:
            if "-" in hostname:
                agent_id = int(hostname.split("-")[-1])
        except ValueError:
            pass

        return {
            "agent": hostname,
            "agent_id": agent_id,
            "timestamp": timestamp, # Bây giờ nó là số nguyên (int), code sẽ hết lỗi
            "cpu": metrics.get("cpu_percent", 0.0),
            "memory": metrics.get("memory_percent", 0.0),
            "disk_read": metrics.get("disk_read_mb", 0.0),
            "disk_write": metrics.get("disk_write_mb", 0.0),
            "net_in": metrics.get("net_in_mb", 0.0),
            "net_out": metrics.get("net_out_mb", 0.0),
        }

    def _index_metric(self, metric_data: Dict[str, Any]) -> bool:
        """
        Index một metric vào Elasticsearch
        """
        try:
            return self.es_client.index_metric(
                agent=metric_data["agent"],
                agent_id=metric_data["agent_id"],
                timestamp=metric_data["timestamp"],
                cpu=metric_data["cpu"],
                memory=metric_data["memory"],
                disk_read=metric_data["disk_read"],
                disk_write=metric_data["disk_write"],
                net_in=metric_data["net_in"],
                net_out=metric_data["net_out"],
            )
        except Exception as e:
            print(f"Error indexing metric: {e}")
            return False

    def process_message(self, msg) -> bool:
        """Process một Kafka message"""
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            return False

        try:
            # Decode message
            key = msg.key().decode("utf-8") if msg.key() else None
            value = json.loads(msg.value().decode("utf-8"))

            # Parse và index
            metric_data = self._parse_metric_data(value)
            success = self._index_metric(metric_data)

            if success:
                self.indexed_count += 1
                if self.indexed_count % 100 == 0:
                    print(
                        f"✓ Indexed {self.indexed_count} metrics (errors: {self.error_count})"
                    )
            else:
                self.error_count += 1

            return success

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            self.error_count += 1
            return False
        except Exception as e:
            print(f"Error processing message: {e}")
            self.error_count += 1
            return False

    def start(self):
        """Bắt đầu consumer loop"""
        print("Starting Elasticsearch Indexer...")
        print(f"  Kafka: {Config.KAFKA_BOOTSTRAP_SERVER}")
        print(f"  Topic: {Config.MONITORING_TOPIC}")
        print(f"  Elasticsearch: http://{self.es_client.host}:{self.es_client.port}")
        print(f"  Index: {self.es_client.index_name}")
        print("Press Ctrl+C to stop\n")

        # Check Elasticsearch connection
        try:
            if not self.es_client.es.ping():
                print("ERROR: Cannot connect to Elasticsearch!")
                return
        except Exception as e:
            print(f"ERROR: Cannot connect to Elasticsearch: {e}")
            return

        self.running = True

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                self.process_message(msg)

        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt")
        finally:
            self.stop()

    def stop(self):
        """Dừng consumer"""
        if not self.running:
            return

        self.running = False
        self.consumer.close()

        print(f"\n✓ Indexer stopped")
        print(f"  Total indexed: {self.indexed_count}")
        print(f"  Total errors: {self.error_count}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Elasticsearch Indexer - Đọc từ Kafka và index vào Elasticsearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--kafka",
        type=str,
        default=None,
        help=f"Kafka bootstrap server (default: {Config.KAFKA_BOOTSTRAP_SERVER})",
    )
    parser.add_argument(
        "--es-host",
        type=str,
        default="localhost",
        help="Elasticsearch host (default: localhost)",
    )
    parser.add_argument(
        "--es-port",
        type=int,
        default=9200,
        help="Elasticsearch port (default: 9200)",
    )
    parser.add_argument(
        "--index",
        type=str,
        default="agent-metrics",
        help="Elasticsearch index name (default: agent-metrics)",
    )
    parser.add_argument(
        "--consumer-group",
        type=str,
        default="elasticsearch-indexer",
        help="Kafka consumer group ID (default: elasticsearch-indexer)",
    )

    args = parser.parse_args()

    # Create và start indexer
    indexer = ElasticsearchIndexer(
        kafka_bootstrap_server=args.kafka,
        elasticsearch_host=args.es_host,
        elasticsearch_port=args.es_port,
        index_name=args.index,
        consumer_group_id=args.consumer_group,
    )

    indexer.start()


if __name__ == "__main__":
    main()
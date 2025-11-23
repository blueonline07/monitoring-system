"""
Analysis Application - CLI tool to read metrics and send commands via Kafka
"""

import os
import json
import time
import socket
from confluent_kafka import Consumer, Producer
import dotenv
dotenv.load_dotenv()

from shared.config import KafkaTopics


class AnalysisApp:
    """Analysis application: reads metrics and sends commands via Kafka"""

    def __init__(
        self,
        bootstrap_servers: str = None,
        group_id: str = "analysis-app-group",
    ):
        if bootstrap_servers is None:
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        # Consumer for metrics
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
        
        # Producer for commands
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers
        })

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
    
    def send_command(self, agent_id: str, command_type: str, params: dict = None):
        """
        Send a command to an agent via Kafka
        
        Args:
            agent_id: Target agent ID
            command_type: Command type (START, STOP, UPDATE_CONFIG, RESTART, STATUS)
            params: Optional command parameters
        """
        if params is None:
            params = {}
        
        command_data = {
            'agent_id': agent_id,
            'type': command_type,
            'params': params,
            'timestamp': int(time.time())
        }
        
        print(f"[DEBUG] Sending command to Kafka: {command_data}")
        
        # Produce command to Kafka
        self.producer.produce(
            KafkaTopics.COMMANDS,
            value=json.dumps(command_data).encode('utf-8'),
            callback=lambda err, msg: self._delivery_callback(err, msg, command_data)
        )
        
        # Wait for delivery
        self.producer.flush()
        
        print(f"✓ Command sent: {command_type} to agent {agent_id}")
    
    def _delivery_callback(self, err, msg, command_data):
        """Callback for message delivery"""
        if err:
            print(f"[ERROR] Command delivery failed: {err}")
        else:
            print(f"[DEBUG] Command delivered to topic {msg.topic()}: {command_data}")
    
    def monitor_metrics(self, duration: float = 60.0):
        """
        Continuously monitor and display metrics
        
        Args:
            duration: How long to monitor (seconds)
        """
        print(f"Monitoring metrics for {duration} seconds...")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        count = 0
        
        try:
            while time.time() - start_time < duration:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None or msg.error():
                    continue
                
                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    count += 1
                    self.display_metrics(data)
                except Exception as e:
                    print(f"Error parsing message: {e}")
                    
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        finally:
            print(f"\n✓ Monitored {count} metric(s)")
            self.consumer.close()


def main():
    """Main entry point for CLI application"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analysis Application CLI - Read metrics and send commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all metrics from Kafka
  python3 run_analysis.py get-metrics
  
  # Monitor metrics continuously
  python3 run_analysis.py monitor --duration 60

  # Send START command to agent
  python3 run_analysis.py send-command my-agent START

  # Send STOP command to agent
  python3 run_analysis.py send-command my-agent STOP
  
  # Send STATUS command to agent
  python3 run_analysis.py send-command my-agent STATUS
  
  # Send UPDATE_CONFIG command
  python3 run_analysis.py send-command my-agent UPDATE_CONFIG
        """,
    )

    parser.add_argument(
        "--kafka",
        type=str,
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
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
    
    # Subcommand: monitor
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Continuously monitor and display metrics",
    )
    monitor_parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="How long to monitor in seconds (default: 60.0)",
    )
    
    # Subcommand: send-command
    send_command_parser = subparsers.add_parser(
        "send-command",
        help="Send command to an agent",
    )
    send_command_parser.add_argument(
        "agent_id",
        type=str,
        help="Target agent ID",
    )
    send_command_parser.add_argument(
        "type",
        type=str,
        choices=["START", "STOP", "UPDATE_CONFIG", "RESTART", "STATUS"],
        help="Command type",
    )
    send_command_parser.add_argument(
        "--param",
        action="append",
        help="Command parameters in key=value format (can be specified multiple times)",
    )

    args = parser.parse_args()

    app = AnalysisApp(
        bootstrap_servers=args.kafka,
        group_id=args.group_id,
    )

    if args.command == "get-metrics":
        app.get_all_metrics(timeout=args.timeout)
    elif args.command == "monitor":
        app.monitor_metrics(duration=args.duration)
    elif args.command == "send-command":
        # Parse parameters
        params = {}
        if args.param:
            for param in args.param:
                key, value = param.split('=', 1)
                params[key] = value
        
        app.send_command(args.agent_id, args.type, params)
    
    return 0


if __name__ == "__main__":
    main()

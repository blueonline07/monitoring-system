"""
Configuration - Kafka topics and system settings
"""

import os
import dotenv

dotenv.load_dotenv()


class Config:
    HOST = os.getenv("GRPC_SERVER_HOST", "localhost")
    PORT = int(os.getenv("GRPC_SERVER_PORT", "50051"))
    MONITORING_TOPIC = "metrics"
    COMMAND_TOPIC = "command"
    MONITORING_GROUP_ID = os.getenv("MONITORING_GROUP_ID", "monitoring")
    COMMAND_GROUP_ID = os.getenv("COMMAND_GROUP_ID", "cmd")
    KAFKA_BOOTSTRAP_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_DEFAULT_PARTITION = int(os.getenv("KAFKA_DEFAULT_PARTITIONS", "3"))
    KAFKA_DEFAULT_REPLICATION_FACTOR = int(
        os.getenv("KAFKA_DEFAULT_REPLICATION_FACTOR", "2")
    )
    ETCD_HOST = os.getenv("ETCD_HOST", "localhost")
    ETCD_PORT = int(os.getenv("ETCD_PORT", "2379"))

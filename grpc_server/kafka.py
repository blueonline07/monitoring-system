from confluent_kafka.admin import AdminClient, NewTopic, NewPartitions
from confluent_kafka import Producer, Consumer
from shared import Config


class KafkaWrapper:
    def __init__(self):
        self.__admin = AdminClient({"bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER})
        available_topics = self.__admin.list_topics(timeout=5).topics
        topics = [Config.COMMAND_TOPIC, Config.MONITORING_TOPIC]
        try:
            for topic in topics:
                if topic not in available_topics:
                    new_topic = NewTopic(
                        topic=topic,
                        num_partitions=Config.KAFKA_DEFAULT_PARTITION,
                        replication_factor=Config.KAFKA_DEFAULT_REPLICATION_FACTOR,
                    )
                    self.__admin.create_topics([new_topic], request_timeout=15)

        except Exception as e:
            print(f"Could not auto-create topics: {e}")

        self.__producer = Producer(
            {
                "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER,
            }
        )
        self.__consumer = Consumer(
            {
                "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVER,
                "group.id": Config.COMMAND_GROUP_ID,
                "auto.offset.reset": "earliest",
            }
        )

    def get_producer(self):
        return self.__producer

    def get_consumer(self):
        return self.__consumer

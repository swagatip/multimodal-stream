import time

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "messages"
PARTITIONS = 1
REPLICATION_FACTOR = 1
BROKER_READY_ATTEMPTS = 10
BROKER_RETRY_SECONDS = 2


def wait_for_broker(admin_client: AdminClient) -> None:
    for attempt in range(BROKER_READY_ATTEMPTS):
        try:
            admin_client.list_topics(timeout=5)
            return
        except KafkaException as error:
            if attempt == BROKER_READY_ATTEMPTS - 1:
                raise RuntimeError(
                    f"Kafka at {BOOTSTRAP_SERVERS} did not become ready."
                ) from error

            print("Kafka is not ready yet; retrying...")
            time.sleep(BROKER_RETRY_SECONDS)


def initialize_topic(admin_client: AdminClient) -> None:
    topic = NewTopic(
        TOPIC,
        num_partitions=PARTITIONS,
        replication_factor=REPLICATION_FACTOR,
    )
    topic_future = admin_client.create_topics([topic])[TOPIC]

    try:
        topic_future.result()
    except KafkaException as error:
        kafka_error = error.args[0]
        if (
            isinstance(kafka_error, KafkaError)
            and kafka_error.code() == KafkaError.TOPIC_ALREADY_EXISTS
        ):
            print(f"Topic already exists: {TOPIC}")
            return
        raise

    print(f"Created topic: {TOPIC}")


def main() -> None:
    admin_client = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
    wait_for_broker(admin_client)
    initialize_topic(admin_client)


if __name__ == "__main__":
    main()

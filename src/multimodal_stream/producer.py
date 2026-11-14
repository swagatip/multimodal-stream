from confluent_kafka import KafkaError, Message, Producer

BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "messages"
MESSAGE = "Hello from the Python producer!"
FLUSH_TIMEOUT_SECONDS = 10


class MessageProducer:
    def __init__(self) -> None:
        self._producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})
        self._delivery_errors: list[str] = []

    def report_delivery(self, error: KafkaError | None, message: Message) -> None:
        if error is not None:
            self._delivery_errors.append(str(error))
            return

        print(f"Delivered to {message.topic()} [{message.partition()}]")

    def send_message(self, message_text: str, topic: str = TOPIC) -> None:
        self._delivery_errors.clear()
        self._producer.produce(
            topic,
            value=message_text.encode("utf-8"),
            callback=self.report_delivery,
        )
        remaining_messages = self._producer.flush(timeout=FLUSH_TIMEOUT_SECONDS)

        if remaining_messages:
            raise TimeoutError(
                f"{remaining_messages} message(s) were not delivered within "
                f"{FLUSH_TIMEOUT_SECONDS} seconds."
            )
        if self._delivery_errors:
            raise RuntimeError(
                f"Kafka message delivery failed: {self._delivery_errors[0]}"
            )

        print(f"Sent message to Topic: {topic}")


def main() -> None:
    producer = MessageProducer()
    producer.send_message(MESSAGE)


if __name__ == "__main__":
    main()
from confluent_kafka import Consumer, Message

BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "messages"


class MessageConsumer:
    def __init__(
        self,
        group_id: str = "multimodal-stream-local",
        topic: str = TOPIC,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self.topic = topic
        self._consumer = Consumer(
            {
                "bootstrap.servers": BOOTSTRAP_SERVERS,
                "group.id": group_id,
                "auto.offset.reset": auto_offset_reset,
            }
        )
        self._consumer.subscribe([self.topic])

    def poll_message(self, timeout: float = 1.0) -> Message | None:
        message = self._consumer.poll(timeout=timeout)
        if message is not None and message.error() is not None:
            raise RuntimeError(f"Kafka consumer error: {message.error()}")
        return message

    def has_assignment(self) -> bool:
        return bool(self._consumer.assignment())

    @staticmethod
    def decode_message(message: Message) -> str | None:
        value = message.value()
        if value is None:
            return None
        return value.decode("utf-8")

    def consume_messages(self) -> None:
        print(f"Listening for messages on {self.topic}. Press Ctrl+C to stop.")

        try:
            while True:
                message = self.poll_message()
                if message is None:
                    continue

                value = self.decode_message(message)
                if value is None:
                    print("Received an empty message.")
                else:
                    print(f"Received: {value}")
        except KeyboardInterrupt:
            print("Stopping consumer.")
        finally:
            self.close()

    def close(self) -> None:
        self._consumer.close()


def main() -> None:
    consumer = MessageConsumer()
    consumer.consume_messages()


if __name__ == "__main__":
    main()
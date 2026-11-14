import time
import unittest
from uuid import uuid4

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from multimodal_stream.consumer import MessageConsumer
from multimodal_stream.producer import BOOTSTRAP_SERVERS, MessageProducer

TEST_TOPIC = "messages.integration"


class ProducerConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        admin_client = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
        topics = admin_client.list_topics(timeout=10).topics
        if TEST_TOPIC in topics:
            return

        topic_future = admin_client.create_topics(
            [NewTopic(TEST_TOPIC, num_partitions=1, replication_factor=1)]
        )[TEST_TOPIC]
        try:
            topic_future.result()
        except KafkaException as error:
            kafka_error = error.args[0]
            if (
                not isinstance(kafka_error, KafkaError)
                or kafka_error.code() != KafkaError.TOPIC_ALREADY_EXISTS
            ):
                raise

    def setUp(self) -> None:
        self.producer = MessageProducer()
        self.consumer = MessageConsumer(
            group_id=f"producer-consumer-test-{uuid4().hex}",
            topic=TEST_TOPIC,
            auto_offset_reset="latest",
        )
        self.addCleanup(self.consumer.close)
        self._wait_for_assignment()

    def test_string_message_is_received_unchanged(self) -> None:
        self._assert_round_trip("integration test message")

    def test_empty_string_is_received_as_empty_string(self) -> None:
        self._assert_round_trip("")

    def test_unicode_text_is_received_unchanged(self) -> None:
        self._assert_round_trip("café — 你好")

    def test_idle_consumer_receives_no_message(self) -> None:
        self.assertIsNone(self.consumer.poll_message(timeout=0.2))

    def _assert_round_trip(self, expected: str) -> None:
        self.producer.send_message(expected, topic=TEST_TOPIC)
        deadline = time.monotonic() + 15

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            message = self.consumer.poll_message(timeout=min(1, remaining))
            if message is None:
                continue
            self.assertEqual(self.consumer.decode_message(message), expected)
            return

        self.fail("Consumer did not receive the message within 15 seconds.")

    def _wait_for_assignment(self) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            message = self.consumer.poll_message(timeout=0.1)
            if message is not None:
                self.fail("Received an unexpected message before publishing.")
            if self.consumer.has_assignment():
                message = self.consumer.poll_message(timeout=0.5)
                if message is not None:
                    self.fail("Received an unexpected message before publishing.")
                return

        self.fail("Consumer was not assigned a topic partition within 15 seconds.")

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from multimodal_stream.producer import MessageProducer


class ProducerTests(unittest.TestCase):
    @patch("multimodal_stream.producer.Producer")
    def test_flush_timeout_raises(self, producer_type: MagicMock) -> None:
        producer_type.return_value.flush.return_value = 1
        producer = MessageProducer()

        with self.assertRaisesRegex(TimeoutError, "not delivered within 10 seconds"):
            producer.send_message("test message")

    @patch("multimodal_stream.producer.Producer")
    def test_delivery_error_raises(self, producer_type: MagicMock) -> None:
        producer = producer_type.return_value

        def fail_delivery(*args: object, **kwargs: Any) -> None:
            callback = kwargs["callback"]
            callback(RuntimeError("simulated delivery failure"), None)

        producer.produce.side_effect = fail_delivery
        producer.flush.return_value = 0
        message_producer = MessageProducer()

        with self.assertRaisesRegex(RuntimeError, "Kafka message delivery failed"):
            message_producer.send_message("test message")

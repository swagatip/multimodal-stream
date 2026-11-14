# multimodal-stream

This project explores streaming multimodal data and various concepts around it.

### Configuration to setup Kafka producer-consumer locally

Prerequisites: Docker Desktop and Python 3.10 or later.

1. Start the local Kafka broker from the repository root:

```powershell
docker compose up -d
```
Tip: Run the following to see if docker is running:

```powershell
 docker compose ps
 ```

2. Create a Python virtual environment and install the client dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

3. Initialize the topic before starting the producer or consumer. This script waits for Kafka to become ready and is safe to run more than once:

```powershell
python .\scripts\initialize_kafka_topic.py
```

The script defaults to `localhost:9092`, one partition, and a replication factor of one for the local single-broker setup. Configure appropriate broker access and topic settings before using it with a production cluster.

4. Start the consumer in one terminal. It needs to be running before the producer starts. A new consumer group starts with messages published after it subscribes.

```powershell
python .\src\multimodal_stream\consumer.py
```

5. In a second terminal, start the producer:

```powershell
python .\src\multimodal_stream\producer.py
```

6. Verify that the consumer prints the text message sent by the producer.

7. Stop the consumer with Ctrl+C. Stop Kafka when finished:

```powershell
docker compose down
```

### Tests

Unit tests use mocks and do not require Kafka. Integration tests require the local broker and create/use a separate `messages.integration` topic. Run them separately:

```powershell
$env:PYTHONPATH = ".\src"
python -m unittest discover -s tests\unit -v
python -m unittest discover -s tests\integration -v
```

### Optional Kafka CLI smoke test

These commands run Kafka's bundled command-line tools inside the `kafka` container. Run them from the repository root while the broker is running.

1. Create the topic if it does not exist:

   ```powershell
   docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic messages --partitions 1 --replication-factor 1
   ```

2. List the topics to verify `messages` exists:

   ```powershell
   docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```

3. In one terminal, start a console consumer:

   ```powershell
   docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic messages --from-beginning
   ```

4. In a second terminal, start a console producer:

   ```powershell
   docker compose exec kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic messages
   ```

   Type a message and press Enter. It should appear in the consumer terminal. The `--from-beginning` option also displays messages already in the topic. Press Ctrl+C in each terminal to stop the CLI tools.

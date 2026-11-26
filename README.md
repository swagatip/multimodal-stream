# multimodal-stream

This project explores streaming multimodal data and various concepts around it.

### Configuration to setup Kafka producer-consumer locally

Prerequisites: Docker Desktop and Python 3.10 or later.

1. Configure local SeaweedFS S3 credentials and start Kafka and SeaweedFS from the repository root. Use local-only credentials, and keep these environment variables set in the PowerShell session where you run the application:

```powershell
$env:AWS_ACCESS_KEY_ID = "local-video-access-key"
$env:AWS_SECRET_ACCESS_KEY = "local-video-secret-key-change-me"
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:OBJECT_STORAGE_ENDPOINT_URL = "http://localhost:8333"
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

### Local video object storage with SeaweedFS

SeaweedFS exposes an S3-compatible API for local development. The Compose service stores data in a named volume, so uploaded objects remain after `docker compose down`.

1. Start the SeaweedFS service using the Compose command above. Its S3 API endpoint is `http://localhost:8333`
Note: the link is not a browser console. Use an S3 client configured with the credentials above to access it. Opening the endpoint in a browser sends an unauthenticated request and may return `AccessDenied`.
2. Install project dependencies and set the source path if not already done:

   ```powershell
   python -m pip install -r requirements.txt
   $env:PYTHONPATH = ".\src"
   ```

3. Run the integration test. It creates the `video-chunks` bucket if needed, chunks a sample file, uploads and downloads each chunk, verifies the reconstructed bytes, and removes the test objects:

   ```powershell
   python -m unittest discover -s tests\integration -p test_video_object_storage.py -v
   ```

   To list buckets and confirm `video-chunks` exists:

   ```powershell
   python -c "import boto3, os; s3=boto3.client('s3', endpoint_url=os.environ['OBJECT_STORAGE_ENDPOINT_URL'], region_name='us-east-1'); print([bucket['Name'] for bucket in s3.list_buckets()['Buckets']])"
   ```

`S3ObjectStorage` uses `OBJECT_STORAGE_ENDPOINT_URL` for SeaweedFS and the standard AWS credential/region environment variables. For AWS S3, leave the endpoint unset and use an IAM role or appropriately scoped credentials. The Compose credentials are for local development only. This storage adapter does not yet publish Kafka video events.

### Tests

- Unit tests use mocks and do not require external services.
- Kafka integration tests require the local broker and create/use a separate `messages.integration` topic.
- The video object-storage integration test requires SeaweedFS and its S3 credentials. It creates the `video-chunks` bucket if needed, so the credentials must be allowed to create or access that bucket.

Run the unit and integration test suites separately:

```powershell
$env:PYTHONPATH = ".\src"
python -m unittest discover -s tests\unit -v
python -m unittest discover -s tests\integration -v
```

Integration testing individual files and test cases:

```powershell
$env:PYTHONPATH = ".\src"
python -m unittest discover -s tests\integration -p test_file.py -v
python -m unittest discover -s tests\integration -p test_file.py -k test_case_name -v
```


Unit testing individual files and test cases:

```powershell
$env:PYTHONPATH = ".\src"
python -m unittest discover -s tests\unit -p test_file.py -v
python -m unittest discover -s tests\unit -p test_file.py -k test_case_name -v
```

Unit tests that load the test-only logging configuration from `tests\unit\logging.ini` display `INFO` messages from the `multimodal_stream` package in the console. This configuration is for tests only; applications using any part of the project should configure logging in their own entry point.

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

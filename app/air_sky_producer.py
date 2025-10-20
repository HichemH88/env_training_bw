# producer_opensky.py
import json
import time
import requests
from kafka import KafkaProducer

# Kafka config
KAFKA_BROKER = "kafka:9092"
KAFKA_TOPIC = "my-topic"

# OpenSky API
OPENSKY_URL = "https://opensky-network.org/api/states/all"

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),retries=3,
    request_timeout_ms=30000
)

def fetch_opensky_data():
    try:
        response = requests.get(OPENSKY_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching OpenSky data: {e}")
        return None

def main(poll_interval=10):
    while True:
        data = fetch_opensky_data()
        if data:
            # Send raw data to Kafka topic
            producer.send(KAFKA_TOPIC, data)
            print(f"✅ Sent {len(data.get('states', []))} aircraft states to Kafka")
        time.sleep(poll_interval)

if __name__ == "__main__":
    main()

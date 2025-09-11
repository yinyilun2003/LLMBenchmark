from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_log_to_kafka(log_data: dict):
    producer.send("fastapi-logs", log_data)
    producer.flush()
    print("log topic sent to kafka.")

print("kafka initialized.")
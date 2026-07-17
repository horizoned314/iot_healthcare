import json
import random
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_TOPIC = "healthcare/patient/vitals"


def run_mock_sensor():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_BROKER, 1883, 60)

    print("[MOCK SENSOR] Memulai pengiriman data sensor tiruan...")
    try:
        while True:
            # Generate data tanda-tanda vital yang realistis
            payload = {
                "id_pasien": random.choice(["P-001", "P-002", "P-003"]),
                "waktu": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "bpm": random.randint(70, 95),
                "spo2": random.randint(96, 99),
                "suhu": round(random.uniform(36.2, 37.3), 2),
                "status_alat": "OK",
            }

            payload_json = json.dumps(payload)
            client.publish(MQTT_TOPIC, payload_json)
            print(f"[TERKIRIM] {payload_json}")

            time.sleep(2)  # Kirim data setiap 2 detik

    except KeyboardInterrupt:
        print("\n[MOCK SENSOR] Simulasi dihentikan.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    run_mock_sensor()
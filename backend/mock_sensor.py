import os
import json
import random
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

# --- KONFIGURASI DARI .ENV ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
# Sensor tiruan mengirim data sebagai input, jadi kita gunakan MQTT_TOPIC_INPUT
MQTT_TOPIC = os.getenv("MQTT_TOPIC_INPUT", "healthcare/patient/vitals")


def run_mock_sensor():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"[MOCK SENSOR] Terhubung ke Broker {MQTT_BROKER}:{MQTT_PORT}")
        print(f"[MOCK SENSOR] Memulai pengiriman data ke topik: {MQTT_TOPIC} ...\n")
        
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
        print("\n[MOCK SENSOR] Simulasi dihentikan oleh pengguna.")
    except Exception as e:
        print(f"\n[ERROR] Gagal menjalankan sensor tiruan: {e}")
    finally:
        client.disconnect()
        print("[MOCK SENSOR] Terputus dari broker.")


if __name__ == "__main__":
    run_mock_sensor()
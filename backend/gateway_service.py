import json
import time
from datetime import datetime
import psycopg2
from psycopg2 import Error
import paho.mqtt.client as mqtt

# --- KONFIGURASI ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "healthcare/patient/vitals"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "jakartaku01",
    "database": "db_iot_medis",
}


# --- FUNGSI DATABASE ---
def save_to_db(data):
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        # Di PostgreSQL, kita cek menggunakan "not connection.closed"
        if not connection.closed:
            cursor = connection.cursor()
            query = """
                INSERT INTO riwayat_vitals 
                (id_pasien, waktu, bpm, spo2, suhu, status_alat) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # Konversi string waktu ISO ke format DATETIME
            waktu_dt = datetime.fromisoformat(
                data["waktu"].replace("Z", "+00:00")
            )

            values = (
                data["id_pasien"],
                waktu_dt.strftime("%Y-%m-%d %H:%M:%S"),
                int(data["bpm"]),
                int(data["spo2"]),
                float(data["suhu"]),
                data.get("status_alat", "OK"),
            )

            cursor.execute(query, values)
            connection.commit()
            print(f"[DB BERHASIL] Data pasien {data['id_pasien']} tersimpan.")

    except Error as e:
        print(f"[DB ERROR] Gagal menyimpan data: {e}")
    finally:
        if "connection" in locals() and not connection.closed:
            cursor.close()
            connection.close()


# --- CALLBACKS MQTT ---
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Terhubung ke Broker {MQTT_BROKER}!")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Mendengarkan topik: {MQTT_TOPIC}")
    else:
        print(f"[MQTT] Gagal terhubung, kode error: {reason_code}")


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode("utf-8")
    print(f"\n[MQTT DITERIMA] Topik: {msg.topic}")
    print(f"Payload raw: {payload_str}")

    try:
        # 1. Validasi JSON
        data = json.loads(payload_str)

        # 2. Validasi field wajib ada
        required_keys = ["id_pasien", "waktu", "bpm", "spo2", "suhu"]
        if not all(key in data for key in required_keys):
            print("[VALIDASI GAGAL] JSON tidak memiliki struktur field wajib!")
            return

        # 3. Simpan ke Database
        save_to_db(data)

    except json.JSONDecodeError:
        print("[ERROR] Payload yang diterima bukan format JSON yang valid!")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan sistem: {e}")


# --- JALANKAN SERVICE ---
if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print("[SYSTEM] Memulai Gateway Service...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Gateway Service dihentikan oleh pengguna.")
    except Exception as e:
        print(f"[SYSTEM ERROR] Tidak bisa terhubung ke broker: {e}")
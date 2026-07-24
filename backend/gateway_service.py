import json
import time
from datetime import datetime
import psycopg2
from psycopg2 import Error
import paho.mqtt.client as mqtt

from ai_service import analyze_vitals, load_model

# --- KONFIGURASI ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_INPUT = "healthcare/patient/vitals"
MQTT_TOPIC_OUTPUT = "healthcare/patient/monitor_ews"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "jakartaku01",
    "database": "db_iot_medis",
}


# --- FUNGSI DATABASE ---
def save_to_db(data):
    connection = None
    try:
        connection = psycopg2.connect(**DB_CONFIG)
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
        if connection and not connection.closed:
            cursor.close()
            connection.close()


# --- CALLBACKS MQTT ---
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Terhubung ke Broker {MQTT_BROKER}!")
        # PERBAIKAN 1: Menggunakan MQTT_TOPIC_INPUT (sebelumnya error karena MQTT_TOPIC tidak terdefinisi)
        client.subscribe(MQTT_TOPIC_INPUT)
        print(f"[MQTT] Mendengarkan topik: {MQTT_TOPIC_INPUT}")
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

        # ---> PERBAIKAN 2: EKSEKUSI ANALISIS AI REAL-TIME <---
        # Memanggil fungsi AI yang sudah di-import untuk menganalisis 3 parameter vital
        hasil_ai = analyze_vitals(
            int(data["bpm"]), int(data["spo2"]), float(data["suhu"])
        )
        # Sisipkan hasil AI ke dalam JSON untuk dikirim ke frontend
        data["ai_analysis"] = hasil_ai

        print("-" * 50)
        print(f"[HASIL ANALISIS AI] Pasien: {data['id_pasien']}")
        print(f"Status EWS : {hasil_ai['status_label']}")
        print(f"Tindakan   : {hasil_ai['rekomendasi']}")
        print("-" * 50)

        # ---> PERBAIKAN 3: FORWARD HASIL AI KE TOPIK OUTPUT <---
        # Publish payload yang sudah dilengkapi AI ke topik monitor_ews agar bisa dibaca Vercel / Dashboard
        client.publish(MQTT_TOPIC_OUTPUT, json.dumps(data))
        print(f"[MQTT TERKIRIM] Data EWS dipublish ke: {MQTT_TOPIC_OUTPUT}")

        # 3. Simpan ke Database
        save_to_db(data)

    except json.JSONDecodeError:
        print("[ERROR] Payload yang diterima bukan format JSON yang valid!")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan sistem: {e}")


# --- JALANKAN SERVICE ---
if __name__ == "__main__":
    print("[SYSTEM] Memulai Gateway Service...")
    
    # PERBAIKAN 4: Muat model AI ke memori sebelum broker MQTT berjalan
    load_model()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Gateway Service dihentikan oleh pengguna.")
    except Exception as e:
        print(f"[SYSTEM ERROR] Tidak bisa terhubung ke broker: {e}")
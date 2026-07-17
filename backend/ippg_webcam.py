import json
import time
from datetime import datetime, timezone
import cv2
import numpy as np
import paho.mqtt.client as mqtt
from scipy.signal import butter, filtfilt

# --- KONFIGURASI MQTT ---
MQTT_BROKER = "localhost"
MQTT_TOPIC = "healthcare/patient/vitals"

# Inisialisasi MQTT Client
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    print("[MQTT] Terhubung untuk pengiriman data iPPG.")
except Exception as e:
    print(f"[PERINGATAN] Gagal konek MQTT: {e}. Tetap menjalankan kamera.")


# --- FUNGSI FILTER SINYAL (BANDPASS FILTER) ---
def bandpass_filter(data, fps=30, lowcut=0.8, highcut=2.5):
    """
    Menyaring frekuensi sinyal:
    0.8 Hz = 48 BPM (Batas terendah detak jantung manusia)
    2.5 Hz = 150 BPM (Batas tertinggi detak jantung manusia saat istirahat/ringan)
    """
    nyq = 0.5 * fps
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(3, [low, high], btype="band")
    return filtfilt(b, a, data)


# --- FUNGSI UTAMA IPPG ---
def run_ippg():
    # Gunakan pendeteksi wajah bawaan OpenCV
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # Buka Webcam (0 adalah kamera default laptop)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam tidak ditemukan atau sedang dipakai aplikasi lain.")
        return

    fps = 30  # Asumsi FPS kamera
    buffer_size = fps * 6  # Simpan 6 detik rekaman warna untuk analisis frekuensi
    green_buffer = []
    last_mqtt_send = time.time()
    bpm_est = 0

    print("[IPPG] Kamera terbuka! Posisikan wajah di depan kamera dengan cahaya cukup.")
    print("[IPPG] Tekan tombol 'q' pada jendela kamera untuk keluar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip horizontal agar seperti cermin
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for x, y, w, h in faces:
            # Gambar kotak biru di sekitar wajah
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Ambil Area ROI (Region of Interest) pada daerah DAHI (lebih stabil dari pipi/mulut)
            roi_x = x + int(w * 0.25)
            roi_y = y + int(h * 0.1)
            roi_w = int(w * 0.5)
            roi_h = int(h * 0.2)

            # Gambar kotak hijau di dahi (area yang disensor)
            cv2.rectangle(
                frame,
                (roi_x, roi_y),
                (roi_x + roi_w, roi_y + roi_h),
                (0, 255, 0),
                2,
            )

            # Ekstrak rata-rata warna HIJAU (channel indeks 1 di BGR) pada area dahi
            roi_frame = frame[roi_y : roi_y + roi_h, roi_x : roi_x + roi_w]
            mean_green = np.mean(roi_frame[:, :, 1])
            green_buffer.append(mean_green)

            # Jaga ukuran buffer tetap 6 detik
            if len(green_buffer) > buffer_size:
                green_buffer.pop(0)

            # Jika data sudah terkumpul minimal 4 detik, mulai hitung BPM
            if len(green_buffer) >= (fps * 4):
                try:
                    # 1. Terapkan Bandpass Filter
                    filtered = bandpass_filter(green_buffer, fps=fps)

                    # 2. Hitung Fast Fourier Transform (FFT) untuk mencari frekuensi dominan
                    fft_data = np.abs(np.fft.rfft(filtered))
                    freqs = np.fft.rfftfreq(len(filtered), 1.0 / fps)

                    # 3. Cari puncak frekuensi tertinggi di rentang detak jantung (0.8 - 2.5 Hz)
                    valid_idx = np.where((freqs >= 0.8) & (freqs <= 2.5))[0]
                    if len(valid_idx) > 0:
                        peak_idx = valid_idx[np.argmax(fft_data[valid_idx])]
                        dom_freq = freqs[peak_idx]
                        bpm_est = int(dom_freq * 60)  # Konversi Hz ke BPM

                except Exception:
                    pass  # Abaikan jika ada error kalkulasi sesaat

            # Tampilkan nilai BPM di layar video
            cv2.putText(
                frame,
                f"ESTIMASI BPM: {bpm_est}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            # Kirim ke MQTT Broker setiap 3 detik sekali jika BPM sudah terdeteksi (> 40)
            if bpm_est > 40 and (time.time() - last_mqtt_send) > 3.0:
                payload = {
                    "id_pasien": "P-WEBCAM",  # ID khusus untuk tes kamera
                    "waktu": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "bpm": bpm_est,
                    "spo2": 98,  # SpO2 statis karena butuh inframerah (tidak bisa dari webcam biasa)
                    "suhu": 36.5,  # Suhu statis
                    "status_alat": "OK",
                }
                try:
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                    print(f"[MQTT TERKIRIM] Wajah terdeteksi! BPM: {bpm_est}")
                    last_mqtt_send = time.time()
                except Exception as e:
                    print(f"[MQTT ERROR] Gagal kirim: {e}")

            break  # Fokus pada 1 wajah pertama saja

        # Tampilkan video live di layar
        cv2.imshow("iPPG Heart Rate Monitor (Tim B)", frame)

        # Tekan tombol 'q' untuk keluar
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    mqtt_client.disconnect()


if __name__ == "__main__":
    run_ippg()
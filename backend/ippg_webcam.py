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

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    print("[MQTT] Terhubung untuk pengiriman data iPPG.")
except Exception as e:
    print(f"[PERINGATAN] Gagal konek MQTT: {e}. Tetap menjalankan kamera.")


def bandpass_filter(data, fps, lowcut=0.8, highcut=2.5):
    """
    Filter frekuensi 0.8 Hz (48 BPM) hingga 2.5 Hz (150 BPM).
    FPS sekarang bersifat dinamis sesuai kondisi aktual kamera.
    """
    nyq = 0.5 * fps
    low = lowcut / nyq
    high = highcut / nyq
    # Gunakan orde 2 agar filter tidak terlalu agresif/tidak stabil pada sampel pendek
    b, a = butter(2, [low, high], btype="band")
    return filtfilt(b, a, data)


def run_ippg():
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Webcam tidak ditemukan atau sedang dipakai.")
        return

    # --- UPAYA MENGUNCI EXPOSURE (Tergantung OS & Driver Kamera) ---
    # Untuk Windows (DirectShow): 0.25 biasanya manual, 0.75 auto
    # Untuk Linux (V4L2): 1 manual, 3 auto
    # Jika kamera tetap berkedip/terang-gelap sendiri, kunci exposure lewat software bawaan webcam/OS.
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)  # Sesuaikan angka ini jika layar terlalu gelap/terang

    # Buffer menyimpan tuple: (timestamp, mean_green)
    data_buffer = []
    buffer_duration = 6.0  # Simpan 6 detik data temporal

    last_mqtt_send = time.time()
    bpm_smooth = 0.0
    
    # Variabel untuk menghaluskan getaran kotak wajah (ROI Smoothing)
    smooth_x, smooth_y, smooth_w, smooth_h = 0, 0, 0, 0

    print("[IPPG] Kamera terbuka! Pastikan pencahayaan terang dan konstan (hindari lampu neon yang berkedip).")
    print("[IPPG] Tekan tombol 'q' untuk keluar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Deteksi wajah dengan parameter sedikit lebih ketat mengurangi salah deteksi
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6, minSize=(100, 100))

        for x, y, w, h in faces:
            # 1. ROI Smoothing (Exponential Moving Average untuk posisi kotak agar tidak bergetar)
            if smooth_w == 0:
                smooth_x, smooth_y, smooth_w, smooth_h = x, y, w, h
            else:
                alpha_roi = 0.2
                smooth_x = int(alpha_roi * x + (1 - alpha_roi) * smooth_x)
                smooth_y = int(alpha_roi * y + (1 - alpha_roi) * smooth_y)
                smooth_w = int(alpha_roi * w + (1 - alpha_roi) * smooth_w)
                smooth_h = int(alpha_roi * h + (1 - alpha_roi) * smooth_h)

            cv2.rectangle(frame, (smooth_x, smooth_y), (smooth_x + smooth_w, smooth_y + smooth_h), (255, 0, 0), 2)

            # Ambil Area Dahi
            roi_x = smooth_x + int(smooth_w * 0.25)
            roi_y = smooth_y + int(smooth_h * 0.08)
            roi_w = int(smooth_w * 0.5)
            roi_h = int(smooth_h * 0.15)

            cv2.rectangle(frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 2)

            # Ekstrak rata-rata warna HIJAU
            roi_frame = frame[roi_y:roi_y + roi_h, roi_x:roi_x + roi_w]
            if roi_frame.size > 0:
                mean_green = np.mean(roi_frame[:, :, 1])
                data_buffer.append((current_time, mean_green))

            # Buang data yang lebih tua dari buffer_duration (6 detik)
            while len(data_buffer) > 0 and (current_time - data_buffer[0][0]) > buffer_duration:
                data_buffer.pop(0)

            # 2. Kalkulasi jika data sudah terkumpul minimal 4 detik dan sampel cukup banyak
            if len(data_buffer) >= 60 and (current_time - data_buffer[0][0]) >= 4.0:
                try:
                    # Hitung FPS AKTUAL secara real-time berdasarkan timestamps
                    timestamps = [item[0] for item in data_buffer]
                    green_vals = [item[1] for item in data_buffer]
                    
                    elapsed = timestamps[-1] - timestamps[0]
                    actual_fps = len(data_buffer) / elapsed

                    # Detrend sederhana (kurangi rata-rata agar berpusat di 0)
                    green_vals = np.array(green_vals) - np.mean(green_vals)

                    # Terapkan Bandpass Filter dengan FPS aktual
                    filtered = bandpass_filter(green_vals, fps=actual_fps)

                    # 3. FFT dengan Zero-Padding (n=2048) untuk resolusi frekuensi tinggi (~0.3 BPM/bin)
                    n_fft = 2048
                    fft_data = np.abs(np.fft.rfft(filtered, n=n_fft))
                    freqs = np.fft.rfftfreq(n_fft, 1.0 / actual_fps)

                    # Cari frekuensi dominan di rentang detak jantung normal (0.8 - 2.5 Hz)
                    valid_idx = np.where((freqs >= 0.8) & (freqs <= 2.5))[0]
                    if len(valid_idx) > 0:
                        peak_idx = valid_idx[np.argmax(fft_data[valid_idx])]
                        dom_freq = freqs[peak_idx]
                        raw_bpm = dom_freq * 60

                        # 4. BPM Smoothing (EMA) agar tidak melompat drastis
                        if bpm_smooth == 0.0:
                            bpm_smooth = raw_bpm
                        else:
                            # 15% nilai baru, 85% nilai lama (sangat stabil)
                            bpm_smooth = (0.15 * raw_bpm) + (0.85 * bpm_smooth)

                except Exception as e:
                    pass  # Abaikan error kalkulasi sesaat

            # Tampilkan nilai BPM
            display_bpm = int(round(bpm_smooth)) if bpm_smooth > 0 else 0
            cv2.putText(
                frame,
                f"ESTIMASI BPM: {display_bpm}",
                (smooth_x, smooth_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            # Kirim ke MQTT setiap 3 detik
            if display_bpm > 40 and (current_time - last_mqtt_send) > 3.0:
                payload = {
                    "id_pasien": "P-WEBCAM",
                    "waktu": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "bpm": display_bpm,
                    "spo2": 98,
                    "suhu": 36.5,
                    "status_alat": "OK",
                }
                try:
                    mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
                    print(f"[MQTT TERKIRIM] BPM: {display_bpm} | FPS Aktual: {actual_fps:.1f}")
                    last_mqtt_send = current_time
                except Exception as e:
                    print(f"[MQTT ERROR] Gagal kirim: {e}")

            break  # Fokus 1 wajah

        cv2.imshow("iPPG Heart Rate Monitor (Tim B)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    mqtt_client.disconnect()


if __name__ == "__main__":
    run_ippg()
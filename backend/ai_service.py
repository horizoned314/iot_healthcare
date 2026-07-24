import os
import joblib
import pandas as pd

MODEL_PATH = "data/model_ews.pkl"
model_ews = None

def load_model():
    """Memuat model ke memori RAM saat server pertama kali dinyalakan."""
    global model_ews
    if os.path.exists(MODEL_PATH):
        model_ews = joblib.load(MODEL_PATH)
        print("[AI SERVICE] Otak AI (Random Forest EWS) berhasil dimuat ke memori!")
    else:
        print(f"[ERROR] File {MODEL_PATH} tidak ditemukan! Harap jalankan train_model.py terlebih dahulu.")

def analyze_vitals(bpm, spo2, suhu):
    """
    Menerima input 3 parameter vital dan mengembalikan status EWS beserta rekomendasi klinis.
    """
    global model_ews
    if model_ews is None:
        load_model()
        if model_ews is None:
            return {
                "status_code": -99,
                "status_label": "MODEL_ERROR",
                "color": "#808080",
                "rekomendasi": "Sistem AI tidak aktif. Periksa server backend."
            }

    # Format input menjadi DataFrame dengan nama kolom yang persis sama saat training
    # Ini mencegah munculnya UserWarning dari scikit-learn
    input_data = pd.DataFrame([[bpm, spo2, suhu]], columns=["bpm", "spo2", "suhu"])
    
    # Lakukan prediksi (hasilnya adalah angka -1, 0, 1, 2, atau 3)
    prediction = int(model_ews.predict(input_data)[0])
    
    # Peta klasifikasi berdasarkan standar medis NEWS2
    if prediction == -1:
        return {
            "status_code": -1,
            "status_label": "ARTEFAK / ERROR SENSOR",
            "color": "#6c757d",  # Abu-abu
            "rekomendasi": "Data tidak wajar! Periksa posisi wajah pasien pada kamera atau stabilitas cahaya."
        }
    elif prediction == 0:
        return {
            "status_code": 0,
            "status_label": "NORMAL",
            "color": "#28a745",  # Hijau
            "rekomendasi": "Kondisi fisiologis stabil. Lanjutkan pemantauan rutin 4-6 jam sekali."
        }
    elif prediction == 1:
        return {
            "status_code": 1,
            "status_label": "WASPADA (NEWS2: Low)",
            "color": "#ffc107",  # Kuning
            "rekomendasi": "Terdapat penyimpangan ringan. Tingkatkan frekuensi pemantauan menjadi setiap 1 jam."
        }
    elif prediction == 2:
        return {
            "status_code": 2,
            "status_label": "BAHAYA (NEWS2: Medium)",
            "color": "#fd7e14",  # Oranye
            "rekomendasi": "Peringatan dini! Siapkan intervensi medis, berikan terapi oksigen jika perlu, dan hubungi dokter jaga."
        }
    elif prediction == 3:
        return {
            "status_code": 3,
            "status_label": "KRITIS (NEWS2: High)",
            "color": "#dc3545",  # Merah
            "rekomendasi": "DARURAT MEDIS! Segera lakukan tindakan resusitasi dan persiapkan pemindahan ke ICU!"
        }